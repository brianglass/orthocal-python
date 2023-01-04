from rest_framework import renderers


class JSONRenderer(renderers.JSONRenderer):    
    def get_indent(self, accepted_media_type, renderer_context):
        return super().get_indent(accepted_media_type, renderer_context) or 4
