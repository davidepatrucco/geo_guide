from .poi import ensure_indexes as _poi_idx
from .poi_doc import ensure_indexes as _poidoc_idx
from .narration_cache import ensure_indexes as _ncache_idx
from .user_contrib import ensure_indexes as _ucontrib_idx
from .usage_log import ensure_indexes as _ulog_idx
from .user import ensure_indexes as _user_idx
from .app_config import ensure_indexes as _appcfg_idx

def ensure_all_indexes():
    _poi_idx(); _poidoc_idx(); _ncache_idx(); _ucontrib_idx(); _ulog_idx(); _user_idx(); _appcfg_idx()