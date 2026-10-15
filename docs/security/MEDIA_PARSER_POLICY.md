# Media and XML parser policy

Maintained for [KAN-244](https://alex-orr.atlassian.net/browse/KAN-244).

## Supported behaviour

Research video intake accepts bounded MOV/MP4 and Matroska/WebM files whose
selected video uses H.264, HEVC, VP8, VP9 or AV1. The file signature selects a
fixed demuxer. MP4/MOV external references are disabled. Only local file and pipe
protocols are available. Three approximate timestamp samples are extracted;
audio, subtitles, hidden tracks and full motion are not analysed.

FFprobe opens decoders for all tracks before selecting its displayed stream.
Consequently the input decoder allowlist applies before both FFprobe and FFmpeg
open the input, including unselected tracks. It includes common AAC, MP3, Opus,
Vorbis and PCM audio decoder implementations to preserve ordinary video files.
An unsupported track can reject the entire file. The reported selected video
codec is independently validated before frame extraction.

The list is defined once in `backend/src/ase/adapters/research_media/video.py`.
Adding a codec or implementation alias requires a review of its native advisories
and a real-runtime compatibility test. The output PNG encoder is not an input
decoder permission. The fixed scale filter and PNG output are unchanged.

XML intake uses DefusedXML with explicit DTD rejection, including internal DTDs
which declare attributes without entities. Feed adapters retain sanitised
`FeedFetchError` failures; research and camera callers retain their existing
failure handling and cached-data behaviour.

## Security boundary and limits

Authentication, object authorisation, upload limits, deadlines and parser process
isolation remain mandatory. Compose's parser has no network, a read-only root,
bounded writable temporary storage, no new privileges and dropped capabilities.
Subprocess tools receive a small fixed environment and no application credentials.
Tesseract receives regenerated PNG pixels and the packaged English model only.

A decoder allowlist is not an AVParser allowlist. Native packet parsers may run
before decoder opening. It does not fix vulnerabilities in allowed decoders,
container parsing, PNG encoding or other installed native libraries. Do not use
these controls as a reason to suppress scanner findings.

Python's bundled libraries can differ from Debian packages in the same image.
Verify runtime versions and dynamic linkage before attributing a package finding
to a Python call. Do not remove linked runtime dependencies merely to reduce a
scanner count, or mix unstable Debian packages into the stable runtime.

## Verification and review

`test_media_codec_policy.py` checks every native input command and rejects
unsupported/missing metadata before sampling. `test_media_video_runtime.py`
checks ordinary audio-bearing files and synthetic CFHD in selected and secondary
tracks. `test_xml_dtd_boundary.py` covers all ten changed XML boundaries, including
UTF-16 camera documents. The tests use synthetic inputs, not exploit bitstreams.

The October advisory ledger and full immutable-image inventories are retained in
Codex Security artifacts and recorded on KAN-244. That dated assessment is distinct
from the September [base-image review](API_BASE_IMAGE_TRIAGE.md). It records
absent components, excluded prerequisites, candidate mitigations and unresolved
native paths separately. A fixable-only image gate does not mean a clean full scan.

Codex owns technical follow-up; Alex Orr owns release and any residual-risk
acceptance. Review the remaining advisories by 23 October 2026, or before release,
image refresh, new media formats, tool flags, models or mounts, whichever is earlier.
This policy does not accept residual risk or verify a live deployment.
