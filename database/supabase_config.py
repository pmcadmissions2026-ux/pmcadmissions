import requests
import os
from supabase import create_client, Client
from config import Config


class SupabaseDB:
    """Supabase Database Connection Handler with REST fallbacks."""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Delay client creation until first access to avoid import-time
        # side-effects in serverless/read-only environments.
        return

    def _ensure_rest_fallback(self, key: str):
        """Prepare REST fallback settings when client creation is not possible."""
        self._use_rest = True
        self._rest_key = key
        self._rest_url = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None

    @property
    def client(self) -> Client:
        """Get or create Supabase client (lazy)."""
        if self._client is None:
            try:
                key_to_use = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
                if key_to_use:
                    key_to_use = key_to_use.strip()
                masked = None
                try:
                    masked = (f"{key_to_use[:4]}...{key_to_use[-4:]}" if key_to_use else None)
                except Exception:
                    masked = None
                key_type = (
                    'SERVICE'
                    if (Config.SUPABASE_SERVICE_KEY and Config.SUPABASE_SERVICE_KEY.strip())
                    else ('ANON' if (Config.SUPABASE_KEY and Config.SUPABASE_KEY.strip()) else 'NONE')
                )
                print(f"Creating Supabase client using {key_type} key: {masked}")

                try:
                    # Try primary key (service if present else anon)
                    self._client = create_client(Config.SUPABASE_URL, key_to_use)
                except Exception as primary_exc:
                    print(f"Primary Supabase client creation failed: {primary_exc}")
                    # Only attempt anon fallback if we attempted service key
                    if key_type == 'SERVICE' and Config.SUPABASE_KEY:
                        anon_key = Config.SUPABASE_KEY.strip() if Config.SUPABASE_KEY else None
                        if anon_key:
                            try:
                                print("Attempting fallback to ANON key for Supabase client")
                                self._client = create_client(Config.SUPABASE_URL, anon_key)
                            except Exception as fallback_exc:
                                print(f"Fallback anon client creation failed: {fallback_exc}")
                                try:
                                    self._ensure_rest_fallback(anon_key)
                                except Exception:
                                    pass
                                # re-raise original exception to surface the root cause
                                raise primary_exc
                    else:
                        raise
            except TypeError as te:
                print("Error creating Supabase client (TypeError):", te)
                raise
            except Exception as e:
                print("Unexpected error creating Supabase client:", e)
                raise
        return self._client

    def execute_query(self, query: str):
        """Execute raw SQL query via Supabase RPC 'query'."""
        try:
            response = self.client.rpc('query', {'sql': query})
            return response
        except Exception as e:
            print(f"Database Query Error: {str(e)}")
            return None

    def select(self, table: str, columns: str = "*", filters: dict = None):
        """SELECT rows from a table. Returns list of rows or [] on failure."""
        # Try SDK first
        try:
            q = self.client.table(table).select(columns)
            if filters:
                for key, value in filters.items():
                    q = q.eq(key, value)
            response = q.execute()
            return response.data if response and getattr(response, 'data', None) is not None else []
        except Exception as e:
            print(f"Select via SDK failed: {e}")

        # REST fallback
        try:
            if getattr(self, '_use_rest', False) and self._rest_url and getattr(self, '_rest_key', None):
                headers = {
                    'apikey': self._rest_key,
                    'Authorization': f'Bearer {self._rest_key}',
                }
                params = {'select': columns}
                if filters:
                    for k, v in filters.items():
                        params[k] = f'eq.{v}'
                url = f"{self._rest_url}/rest/v1/{table}"
                r = requests.get(url, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    try:
                        return r.json()
                    except Exception:
                        return []
                else:
                    print(f"REST select failed status={r.status_code} body={r.text}")
                    return []
        except Exception as e:
            print(f"Select REST fallback error: {e}")

        return []

    def insert(self, table: str, data: dict):
        """INSERT a row. Returns inserted row(s) or None on failure."""
        try:
            response = self.client.table(table).insert(data).execute()
            return response.data if response and getattr(response, 'data', None) is not None else None
        except Exception as e:
            print(f"Insert via SDK failed: {e}")

        try:
            # Always attempt REST fallback when SDK insert fails, using available keys.
            rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
            rest_url = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
            if rest_key and rest_url:
                rest_key = rest_key.strip()
                headers = {
                    'apikey': rest_key,
                    'Authorization': f'Bearer {rest_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=representation',
                }
                url = f"{rest_url}/rest/v1/{table}"
                r = requests.post(url, headers=headers, json=data, timeout=10)
                if r.status_code in (200, 201):
                    try:
                        return r.json()
                    except Exception:
                        return None
                else:
                    print(f"REST insert failed status={r.status_code} body={r.text}")
                    return None
        except Exception as e:
            print(f"Insert REST fallback error: {e}")
        except Exception as e:
            print(f"Insert REST fallback error: {e}")

        print(f"Insert Error in table '{table}': no available client")
        return None

    def update(self, table: str, data: dict = None, filters: dict = None, **kwargs):
        """UPDATE rows matching filters. Supports both signatures:
        - update(table, data, filters)
        - update(table, filters=..., data=...)
        Returns updated rows or None.
        """
        # Normalize parameters from positional or keyword usage
        # If caller passed (table, data, filters) as positional args, Python will map correctly.
        # But some call sites use update(table, filters_dict, data_dict) accidentally;
        # detect that case and swap when types suggest it.
        if data is None and 'data' in kwargs:
            data = kwargs.get('data')
        if filters is None and 'filters' in kwargs:
            filters = kwargs.get('filters')

        # Heuristic: if data looks like filters (contains keys typically used as filters like 'user_id' or 'id')
        # and filters looks like an update payload (contains non-filter keys), swap them.
        try:
            if isinstance(data, dict) and isinstance(filters, dict):
                # If data only contains keys that are typical filter names and filters contains other keys, swap.
                filter_like_keys = {'user_id', 'id', 'email', 'employee_id', 'app_id', 'student_id'}
                data_keys = set(data.keys())
                filter_keys = set(filters.keys())
                if data_keys & filter_like_keys and not (filter_keys & filter_like_keys):
                    # swap
                    data, filters = filters, data
        except Exception:
            pass

        try:
            # Build update request then apply filters (eq) on the request builder
            req = self.client.table(table).update(data or {})
            if filters:
                for key, value in filters.items():
                    # The request builder exposes `eq` for filtering after update()
                    req = req.eq(key, value)
            response = req.execute()
            return response.data if response and getattr(response, 'data', None) is not None else None
        except Exception as e:
            print(f"Update via SDK failed: {e}")

        try:
            if getattr(self, '_use_rest', False) and self._rest_url and getattr(self, '_rest_key', None):
                headers = {
                    'apikey': self._rest_key,
                    'Authorization': f'Bearer {self._rest_key}',
                    'Content-Type': 'application/json',
                }
                params = {}
                if filters:
                    for k, v in filters.items():
                        params[k] = f'eq.{v}'
                url = f"{self._rest_url}/rest/v1/{table}"
                r = requests.patch(url, headers=headers, params=params, json=data, timeout=10)
                if r.status_code in (200, 204):
                    try:
                        return r.json() if r.text else []
                    except Exception:
                        return []
                else:
                    print(f"REST update failed status={r.status_code} body={r.text}")
                    return None
        except Exception as e:
            print(f"Update REST fallback error: {e}")

        return None

    def delete(self, table: str, filters: dict):
        """DELETE rows matching filters. Returns deleted rows or None."""
        try:
            q = self.client.table(table)
            if filters:
                for key, value in filters.items():
                    q = q.eq(key, value)
            response = q.delete().execute()
            return response.data if response and getattr(response, 'data', None) is not None else None
        except Exception as e:
            print(f"Delete via SDK failed: {e}")

        try:
            if getattr(self, '_use_rest', False) and self._rest_url and getattr(self, '_rest_key', None):
                headers = {
                    'apikey': self._rest_key,
                    'Authorization': f'Bearer {self._rest_key}',
                }
                params = {}
                if filters:
                    for k, v in filters.items():
                        params[k] = f'eq.{v}'
                url = f"{self._rest_url}/rest/v1/{table}"
                r = requests.delete(url, headers=headers, params=params, timeout=10)
                if r.status_code in (200, 204):
                    try:
                        return r.json() if r.text else []
                    except Exception:
                        return []
                else:
                    print(f"REST delete failed status={r.status_code} body={r.text}")
                    return None
        except Exception as e:
            print(f"Delete REST fallback error: {e}")

        return None

    def count(self, table: str, filters: dict = None) -> int:
        """Return count of rows in a table, using SDK or REST fallback."""
        try:
            q = self.client.table(table).select("*", count="exact")
            if filters:
                for key, value in filters.items():
                    q = q.eq(key, value)
            response = q.execute()
            return response.count if response and getattr(response, 'count', None) is not None else 0
        except Exception as e:
            print(f"Count via SDK failed: {e}")

        try:
            if getattr(self, '_use_rest', False) and self._rest_url and getattr(self, '_rest_key', None):
                headers = {
                    'apikey': self._rest_key,
                    'Authorization': f'Bearer {self._rest_key}',
                    'Prefer': 'count=exact',
                }
                params = {'select': 'id'}
                if filters:
                    for k, v in filters.items():
                        params[k] = f'eq.{v}'
                url = f"{self._rest_url}/rest/v1/{table}"
                r = requests.get(url, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    # Supabase returns Content-Range header like: 0-9/123
                    cr = r.headers.get('Content-Range') or r.headers.get('content-range')
                    if cr and '/' in cr:
                        try:
                            return int(cr.split('/')[-1])
                        except Exception:
                            pass
                    try:
                        data = r.json()
                        return len(data) if isinstance(data, list) else 0
                    except Exception:
                        return 0
                else:
                    print(f"REST count failed status={r.status_code} body={r.text}")
                    return 0
        except Exception as e:
            print(f"Count REST fallback error: {e}")

        return 0


# Singleton instance
db = SupabaseDB()
