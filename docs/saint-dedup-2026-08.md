# Saint-identity duplicate consolidation, August 2026

## Background

Follow-on to `docs/saint-model-refactor.md` (PR #150, merged). That project's Stage 4 did a full pairwise duplicate survey (Jaccard token-overlap, threshold 0.4) across the ~1000 `Saint` rows that existed at the time and merged 25 confirmed pairs, requiring explicit cross-reference text in the source as the only reliable auto-confirm signal. Stage 11 (later, separate) added ~693 new `Saint` rows from a Greek-tradition harvest and deduped them against *existing* content, but never re-ran a fresh whole-corpus consolidation pass.

Surfaced 2026-08-03 while reviewing what the (not-yet-shipped) MCP server's `search_saints` tool returns: St Seraphim of Sarov is split across two unlinked `Saint` rows (repose, pk 5111, vs. relics-uncovering, pk 5550) -- exactly the fragmentation problem Stage 4 existed to fix, missed because "Repose of..." vs. "Uncovering of the relics (1903) of..." only share 2/6 tokens (Jaccard 0.33), just under the 0.4 threshold used at the time.

**Empirical scoping** (done before committing to an approach): a blind Jaccard rescan mirroring Stage 4's exact technique produced 2,144 candidates (~8x the original 287), verified by sampling to be dominated by noise from shared ecclesiastical-office vocabulary ("Patriarch of Constantinople," "Bishop of X") among the ~725 Greek-tradition `Saint` rows (only 5/725 have `full_name` set, vs. 853/934 for `common`-tradition rows, and almost none have story text -- i.e. no reliable signal). Not productive; abandoned in favor of the approach below.

## Approach

Mirrors Stage 11's proven 4-pass structure, in ascending cost order:

1. Cross-reference-text scan (explicit phrases like "his main commemoration is," "also commemorated") -- cheapest, highest precision.
2. Occasion-prefix-normalized exact-token scan.
3. Fuzzy edit-distance scan (`SequenceMatcher` ratio >= 0.8, `autojunk=False`) for transliteration variants.
4. Full day-by-day manual review of all ~366 calendar dates, all three traditions together, tracking a running "seen identities" registry to catch cross-date duplicates.

**Verification bar for every merge**: never on name/token resemblance alone. Require explicit cross-reference text, or matching biographical detail cross-checked against an independent external source (OCA, ROCOR/holytrinityorthodox.com, antiochian.org, goarch.org) when ambiguous. Watch for: common first names alone, shared office/epithet across different centuries/people, joint identities incorrectly absorbing a solo occurrence.

Scope is **all ~366 dates**, not just Stage 11's 315 Greek-harvest-affected ones -- Seraphim, Symeon, and Emilia (below) are all pre-Greek-harvest, `common`/`slavic`-tradition cases outside that narrower scope.

## Progress log

### Pass 1: cross-reference-text scan

61 hits found (regex matched more broadly than the initial estimate). Reviewed all 61 individually rather than trusting the match alone -- most (58/61) were either already correctly linked (same `saint_id` on both ends of the cross-reference) or incidental mentions of a *different* person's commemoration date within a story (teacher/mentor/relative references with a parenthetical date, not an identity-duplicate signal at all -- a false-positive class the generic "commemorated on [month]" pattern is prone to). 3 genuine findings:

- **St Seraphim of Sarov** (Saint 5111, repose Jan 2 vs. Saint 5550, relics-uncovering Jul 19) -- confirmed via each story's own text (5550's story literally ends "Saint Seraphim is commemorated January 2"). Merged: repointed `DayCommemoration` 5679 (Jul 19) onto Saint 5111, deleted Saint 5550. 5111 kept as canonical since its `full_name` includes the death year ("St Seraphim of Sarov (1833)") vs. 5550's plain "St Seraphim of Sarov".
- **St Symeon the New Theologian** (Saint 5681, "repose" Mar 12 vs. Saint 5981, Oct 12) -- Mar 12's story is a pure 47-character stub ("His main commemoration is on October 12"), Oct 12 has the real ~1000-char biography which itself notes "(He reposed on March 12, but since this...[coincides with Lent])". Merged: repointed `DayCommemoration` 5810 (Mar 12) onto Saint 5981, deleted Saint 5681.
- **St Emilia** (Saint 5595, mother of Sts Macrina/Basil the Great/Gregory of Nyssa) -- different shape of bug: not two Saint rows, but *one* Saint with two `DayCommemoration` rows (Jan 1 and May 8), both carrying the identical story text "Her main commemoration is on May 8" -- including on the May 8 entry itself, confirming both are copies of the same stub and Jan 1 is spurious (likely appended there as family background on St Basil the Great's own Jan 1 feast, not a real commemoration of her). Fixed by deleting the Jan 1 `DayCommemoration` row (5724), keeping the May 8 one (5878) and the Saint row itself.

**Also noted, not acted on**: `dc=5401` (St Cyril of Alexandria, solo Saint 5292, Jun 9 repose) references Jan 18 as "the date of his restoration to his see" -- but unlike Athanasius (who got a solo Jan-18 split in the original Stage 4), Cyril has no dedicated Jan-18 `DayCommemoration` pointing to his solo identity; that occasion is still only visible via the joint "Ss Athanasius the Great and Cyril of Alexandria" Saint. This isn't a duplicate to merge (there's no second Cyril row), just an asymmetry in how thoroughly the original Athanasius/Cyril split was done -- flagged for Brian, not fixed here (would require adding a new `DayCommemoration` row, not consolidating an existing one).

All verified via `liturgics.Day(...)` spot checks (dates and neighboring commemorations unaffected beyond the intended change) and the full test suite; `calendarium/tests/data/january.json` golden fixture updated for the Emilia removal (confirmed via full-month diff against the live API that it was the *only* change across all of January). 127/127 tests pass.

### Pass 2: occasion-prefix scan

5 candidates found; Seraphim/Symeon were already resolved via Pass 1 (same underlying pairs). The remaining 3 -- Julian the Martyr (3 rows: 3/16, 5/18, 9/12), Marinos the Martyr (2 rows: 3/17, 10/18), Zacharias the New Martyr (2 rows: 3/30, 5/28) -- were checked against the project's cached antiochian.org raw harvest (`data/antiochian_raw/2026-*.json`) since all 7 rows are bare `tradition='greek'` entries with no story or `full_name` to go on internally. Every date's source `feastDayDescription` lists the name with zero disambiguating detail (no epithet, era, or region) alongside a completely different, unrelated set of co-commemorated saints each time -- no cross-reference connecting any of the dates for a given name. Per the verification bar (name resemblance alone is not sufficient -- these are exactly the kind of common martyr name the original project repeatedly found belonged to different historical people), **left all three groups unmerged**. No DB changes this pass.

### Pass 3: fuzzy edit-distance scan

Built a token-level fuzzy scan (`SequenceMatcher` ratio >= 0.8, `autojunk=False`, comparing all ~2070 distinct tokens across the corpus pairwise, then mapping fuzzy-matching token pairs back to candidate Saint pairs with no exact token overlap). Found 598 fuzzy token pairs -> 3,872 candidate Saint pairs -- far more than Stage 11's original 40 hits, because Stage 11 ran this technique on a much narrower search (960 new entries vs. existing corpus, one direction), not all-pairs across the whole ~1667-Saint corpus.

Spot-checked a filtered sample (~80 pairs where both fuzzy tokens are >= 7 characters, to skip short-word coincidences): overwhelmingly noise from genuinely different people who happen to share a Greek/Latin name-root or suffix variant (Eutychios/Eutychianos/Eutychius/Eutychianus are distinct individuals in the source, not spelling variants of one person; Cappadocia/Cappadocian, Thessalonica/Thessalonika/Thessaloniki are place-name adjective forms shared by unrelated people "of" that place). **One genuine hit** found by checking story content, not name similarity alone:

- **Hieromartyr Theodoretus** (Saint 5674, `common`, Mar 8 -- full story: priest, custodian of a cathedral in Antioch, martyred under Julian the Apostate) and **Theodoretos the Holy Martyr of Antioch** (Saint 6298, `greek`, Mar 3, no story) -- same era, same city, same circumstance confirmed via the story text. Different dates per tradition (a real, previously-seen pattern -- St Catherine of Alexandria and Mercurius also have different Slavic vs. Greek commemoration dates). Merged the Saint identity, kept both `DayCommemoration` date rows: repointed the Mar 3 (`greek`) row onto Saint 5674, deleted Saint 6298.

**Conclusion**: like the blind Jaccard rescan, blind fuzzy-token matching across the whole corpus doesn't productively narrow things down on its own -- both hit the same wall (no biographical anchor to confirm identity, especially for the ~725 story-less Greek-tradition rows). Not pursuing further tuning of this technique.

**One more cheap high-precision check run before starting Pass 4**: exact-normalized-name matching (same name, different dates -- would catch a "Gregory of Assa added on 3 separate dates" -style verbatim repeat, the highest-precision signal available). Found only the same 3 already-reviewed-and-left-unmerged groups from Pass 2 (Julian/Marinos/Zacharias) -- nothing new. Between this, the blind Jaccard rescan, the fuzzy-token scan, and the cross-reference-text scan, the algorithmic techniques are now genuinely exhausted; remaining duplicates (if any) use different-enough wording for the same person that no string-matching heuristic can surface them. Pass 4 (manual review) is the only remaining path, exactly as Stage 11 concluded.

**Also run before Pass 4**: a within-day check (same Jaccard technique, scoped to pairs on the *same* calendar date rather than the whole corpus -- much less noisy since the candidate pool per day is tiny). Found only 6 candidates across the whole year, all confirmed different people on inspection (e.g. Great Martyr Mercurius (ca. 259) vs. Holy Martyr Mercurius of Smolensk (1238) -- same name, ~900 years apart). No same-day duplication bug has crept back in since Stages 6/9/10 fixed the original version of this problem.

### Pass 4: manual review (scoped to a sample, per Brian's direction)

Given 5 independent techniques (blind Jaccard, occasion-prefix, fuzzy-token, exact-name, within-day) had converged on a small, exhausted result set, discussed scope directly with Brian rather than committing to reading all 366 dates blind. Agreed approach: spot-check a sample of months by hand, then use whatever pattern the sample surfaces to build one more *targeted* algorithmic pass covering the full year -- cheaper and more thorough than manual-only for a pattern that turns out to be well-defined.

**Manually read April, August, and December in full** (135 + 166 + 131 = 432 `DayCommemoration` rows across all traditions, day by day). Found 2 new genuine duplicates, both a specific shape neither the Jaccard nor fuzzy-token scan caught -- a story-less `day_native` (terse-list) entry and a same-day story-bearing *additive* entry for the same person, whose Jaccard score fell just under the 0.5 within-day threshold because of transliteration/spelling differences ("Amasea" vs "Amasia", "20,000" vs "Twenty Thousand"):

- **Hieromartyr Basil of Amasea/Amasia** (Apr 26): Saint 5242 (`day_native`, no story, `rank=3` from the recovered Paul Kachur typikon data) and Saint 5730 (additive, full story about Bishop Basil of Amasia sheltering St Glaphyra from Licinius) -- same person (place name spelled two ways). Merged: moved the story onto the day-native entry (preserving its `rank`), backfilled `full_name`, deleted the additive Saint/`DayCommemoration`.
- **20,000 Martyrs of Nicomedia** (Dec 28): Saint 5510 (`day_native`, no story) and Saint 6088 (additive, full story, "Twenty Thousand" spelled out) -- same event. Same merge pattern.

This is exactly the Stage-3-era bug pattern (a `day_native` entry and a matching additive story entry both surviving unrecognized as the same identity) recurring in a form the original per-day Jaccard check's threshold was too high to catch.

**Built one targeted whole-year scan from this pattern**: every `(day_native, no story)` paired against every same-day `(additive, has story)` row, requiring only 1+ shared non-generic token (much lower threshold than the general within-day check, justified because this specific pairing shape is inherently low-noise -- a real duplicate of this shape is either genuinely obvious or a coincidence, not a spectrum). Found 32 candidates covering the *entire year*, not just the 3 sampled months. Reviewed all 32 individually (checking story content for era/place/circumstance match, not just token overlap):

- **3 more genuine merges** (all same-day, same pattern as above): Hieromartyr Mark, Bishop of Arethusa (Mar 29, story confirms "Bishop of Arethusa in Syria... Julian the Apostate... 361"); St Epiphanius, Bishop of Cyprus (May 12, story confirms "born a Jew in Palestine... became a monk", joint mention of Germanos of Constantinople in the surviving entry is fine, Germanos has no other entry it could be robbing); Martyr Andrew Stratelates/Strateletes (Aug 19, story confirms "officer, a tribune... Persians attacked... title: commander, strateletes").
- **27 correctly left unmerged**, mostly same-common-first-name-different-person (two different Sylvesters, two different Nicholases, two different Gregorys, two different Stephens/Theodores, etc. -- sharing only a generic office token like "bishop"/"hieromartyr"). One deliberately checked in detail and rejected: **Stephen the Martyr** (Sep 24, bare `greek` entry) vs. **St Stephen, First-crowned King of Serbia (Simon the Monk) (1224)** -- the story says he "entered into rest" peacefully as a monk, which doesn't even fit a "martyr" designation, confirming these are different people despite the shared first name.
- Confirmed again (Aug 24, Hieromartyr Eutychius vs. Hieromartyr Eutyches) that the original project's own Stage 2 finding -- these are a deliberately-cleared *wrong* match, not a real duplicate -- still holds; correctly did not re-merge.

**Not done**: the remaining ~9 months' worth of dates were not read line-by-line beyond what the targeted scan above already covers for this specific pattern. Given the targeted scan covers the *entire year* for the "day-native vs. additive, same day" shape (which accounts for 5 of the 7 new finds this pass), and the other techniques (cross-reference-text, fuzzy, exact-name) already covered the whole corpus for their respective patterns, coverage is broad even though not literally exhaustive line-by-line. A true "same person, completely different wording, different day, no shared vocabulary at all" case could still exist undetected -- this is the same residual risk the original project accepted after Stage 11.

## Merges completed (9 total)

- St Seraphim of Sarov: Saint 5550 (relics-uncovering, Jul 19) merged into Saint 5111 (repose, Jan 2).
- St Symeon the New Theologian: Saint 5681 (Mar 12 stub) merged into Saint 5981 (Oct 12, full biography).
- St Emilia: spurious duplicate `DayCommemoration` (Jan 1, pk 5724) deleted; May 8 (pk 5878) kept.
- Hieromartyr Theodoretus: Saint 6298 (Mar 3, greek) merged into Saint 5674 (Mar 8, common) -- same person, tradition-specific date difference retained via separate `DayCommemoration` rows.
- Hieromartyr Basil of Amasea/Amasia (Apr 26): Saint 5730 merged into day-native Saint 5242.
- 20,000 Martyrs of Nicomedia (Dec 28): Saint 6088 merged into day-native Saint 5510.
- Hieromartyr Mark, Bishop of Arethusa (Mar 29): Saint 5695 merged into day-native Saint 5215.
- St Epiphanius, Bishop of Cyprus (May 12): Saint 5754 merged into day-native Saint 5255.
- Martyr Andrew Stratelates (Aug 19): Saint 5885 merged into day-native Saint 5360.

All verified via `liturgics.Day(...)` spot checks (each merged date now shows exactly one entry, no other saints/feasts on the date disturbed) and the full test suite (127/127 passing throughout).

## Reviewed and deliberately left unmerged

- Julian the Martyr (Saints 6339/6512/6842, dates 3/16, 5/18, 9/12) -- common martyr name, no distinguishing detail in source or local data; likely different people.
- Marinos the Martyr (Saints 6342/6936, dates 3/17, 10/18) -- same reasoning.
- Zacharias the New Martyr (Saints 6364/6533, dates 3/30, 5/28) -- same reasoning.
- Stephen the Martyr (Sep 24) vs. St Stephen, First-crowned King of Serbia -- story contradicts a "martyr" designation for the king; different people.
- Hieromartyr Eutychius vs. Hieromartyr Eutyches (Aug 24) -- reconfirmed the original project's own deliberate non-merge still holds.
- ~26 other same-day-native-vs-additive candidates from the targeted scan, all sharing only a generic office/first-name token (bishop, hieromartyr, John, Nicholas, Gregory, Stephen, Theodore, etc.) between clearly different specific people.

(See also "Also noted, not acted on" under Pass 1 for the Cyril of Alexandria asymmetry, which isn't a duplicate but is worth Brian's attention separately)

## Status

Stopped here per explicit direction (spot-check + targeted scan rather than a full literal 366-date read) after 9 confirmed merges across 5 independent techniques, with strong convergent evidence the easily-findable duplicates are now cleared. Branch `saint-dedup-2026-08`, not yet committed or merged.
