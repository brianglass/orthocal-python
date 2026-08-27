import asyncio
import logging
import pickle
import zlib

from contextvars import ContextVar

from asgiref.sync import async_to_sync
from django.core.cache.backends.base import BaseCache
from django.utils.functional import cached_property
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.field_path import FieldPath

logger = logging.getLogger(__name__)

ACLIENT = ContextVar('ACLIENT')

def get_aclient():
    try:
        return ACLIENT.get()
    except LookupError:
        client = firestore.AsyncClient()
        ACLIENT.set(client)
        return client

class FirestoreCache(BaseCache):
    def __init__(self, location, params):
        super().__init__(params)
        self.location = location
        self.params = params

    @property
    def aclient(self):
        # We have to recreate this client every time, otherwise the Firestore
        # client coughs.
        client = get_aclient()
        logger.debug(dir(client))
        try:
            client._transport.grpc_channel._loop = asyncio.get_running_loop()
        except AttributeError:
            pass
        return client

    @cached_property
    def client(self):
        # We have to recreate this client every time, otherwise the Firestore
        # client coughs.
        return firestore.Client()

    def make_key(self, key, version=None):
        key = super().make_key(key, version=version)
        return key.replace('/', '__')

    def encode_value(self, value):
        serialized = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        return zlib.compress(serialized)

    def decode_value(self, value):
        serialized = zlib.decompress(value)
        return pickle.loads(serialized)

    # ASync functions

    async def aget(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        doc_ref = self.aclient.collection(self.location).document(key)
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            logger.debug(f'Got {key} from cache')
            return self.decode_value(data['value'])

    async def aset(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        value = self.encode_value(value)
        doc = self.aclient.collection(self.location).document(key)
        await doc.set({'value': value})
        logger.debug(f'Set {key} in cache')

    async def adelete(self, key, version=None):
        key = self.make_key(key, version=version)
        doc = self.aclient.collection(self.location).document(key)
        await doc.delete()

    async def aclear(self):
        docs = self.aclient.collection(self.location).list_documents()
        async for doc in docs:
            await doc.delete()

    async def aget_many(self, keys, version=None):
        keys = [self.make_key(key, version=version) for key in keys]
        docs = self.aclient.collection(self.location).where('key', 'in', keys).stream()
        return {
            data['key']: self.decode_value(data['value'])
            async for doc in docs if (data := doc.to_dict())
        }

    async def aset_many(self, data, timeout=None, version=None):
        for key, value in data.items():
            key = self.make_key(key, version=version)
            value = self.encode_value(value)
            doc = self.aclient.collection(self.location).document(key)
            await doc.set({'value': value})

    async def adelete_many(self, keys, version=None):
        keys = [self.make_key(key, version=version) for key in keys]
        docs = self.aclient.collection(self.location).where('key', 'in', keys).stream()
        async for doc in docs:
            doc.delete()

    # Sync functions

    def get(self, key, default=None, version=None):
        fkey = self.make_key(key, version=version)
        doc_ref = self.client.collection(self.location).document(fkey)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            logger.debug(f'Got {key} from cache')
            return self.decode_value(data['value'])

    def set(self, key, value, timeout=None, version=None):
        fkey = self.make_key(key, version=version)
        value = self.encode_value(value)
        doc_ref = self.client.collection(self.location).document(fkey)
        doc_ref.set({
            'key': key,
            'value': value,
        })
        logger.debug(f'Set {key} in cache')

    def delete(self, key, version=None):
        fkey = self.make_key(key, version=version)
        doc_ref = self.client.collection(self.location).document(fkey)
        doc_ref.delete()

    def clear(self):
        batch = self.client.batch()

        docs = self.client.collection(self.location).list_documents(page_size=100)
        for doc_ref in docs:
            batch.delete(doc_ref)

        batch.commit()

    def get_many(self, keys, version=None):
        collection = self.client.collection(self.location)
        fkeys = [collection.document(self.make_key(key, version=version)) for key in keys]
        filter = FieldFilter(FieldPath.document_id(), 'in', fkeys)
        docs = collection.where(filter=filter).stream()
        return {
            data['key']: self.decode_value(data['value'])
            for doc in docs if (data := doc.to_dict())
        }

    def set_many(self, data, timeout=None, version=None):
        batch = self.client.batch()

        for key, value in data.items():
            fkey = self.make_key(key, version=version)
            value = self.encode_value(value)
            doc_ref = self.client.collection(self.location).document(fkey)
            batch.set(doc_ref, {
                'key': key,
                'value': value,
            })

        batch.commit()

    def delete_many(self, keys, version=None):
        batch = self.client.batch()

        collection = self.client.collection(self.location)
        fkeys = [collection.document(self.make_key(key, version=version)) for key in keys]
        filter = FieldFilter(FieldPath.document_id(), 'in', fkeys)
        docs = self.client.collection(self.location).where(filter=filter).stream()
        for doc in docs:
            batch.delete(doc.reference)

        batch.commit()
