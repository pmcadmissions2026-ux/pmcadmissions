import os
from supabase import create_client, Client
from config import Config

class SupabaseDB:
    """Supabase Database Connection Handler"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Delay client creation until first access to avoid import-time
        # side-effects in serverless/read-only environments.
        # The actual client is created in the `client` property when needed.
        return
    
    @property
    def client(self) -> Client:
        """Get Supabase client"""
        if self._client is None:
            try:
                # Choose service key when available (server-side) to bypass
                # RLS restrictions for administrative reads. Fall back to the
                # public anon key if service key is not provided.
                key_to_use = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
                if key_to_use:
                    key_to_use = key_to_use.strip()
                masked = None
                try:
                    masked = (f"{key_to_use[:4]}...{key_to_use[-4:]}" if key_to_use else None)
                except Exception:
                    masked = None
                key_type = 'SERVICE' if (Config.SUPABASE_SERVICE_KEY and Config.SUPABASE_SERVICE_KEY.strip()) else ('ANON' if (Config.SUPABASE_KEY and Config.SUPABASE_KEY.strip()) else 'NONE')
                print(f"Creating Supabase client using {key_type} key: {masked}")
                # Try primary key (service if present else anon). If that fails
                # (e.g. truncated/invalid service key in the environment),
                # attempt to fall back to the anon key if available. This makes
                # server-side reads work when tables are public and the
                # service key is misconfigured.
                try:
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
                                # re-raise original exception to surface the root cause
                                raise primary_exc
                    else:
                        # No fallback available; re-raise
                        raise
            except TypeError as te:
                # Some vendored/http client incompatibilities may raise
                # TypeError (unexpected kwargs). Log a helpful message and
                # re-raise so the caller can handle it.
                print("Error creating Supabase client:", te)
                raise
            except Exception as e:
                print("Unexpected error creating Supabase client:", e)
                raise
        return self._client
    
    def execute_query(self, query: str):
        """Execute raw SQL query"""
        try:
            response = self.client.rpc('query', {'sql': query})
            return response
        except Exception as e:
            print(f"Database Query Error: {str(e)}")
            return None
    
    def select(self, table: str, columns: str = "*", filters: dict = None):
        """SELECT query"""
        try:
            query = self.client.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data if response else []
        except Exception as e:
            print(f"Select Error: {str(e)}")
            return []
    
    def insert(self, table: str, data: dict):
        """INSERT query"""
        try:
            response = self.client.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            print(f"Insert Error in table '{table}': {str(e)}")
            print(f"Data attempted: {data}")
            import traceback
            traceback.print_exc()
            return None
    
    def update(self, table: str, data: dict, filters: dict):
        """UPDATE query"""
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Update Error: {str(e)}")
            return None
    
    def delete(self, table: str, filters: dict):
        """DELETE query"""
        try:
            query = self.client.table(table)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.delete().execute()
            return response.data
        except Exception as e:
            print(f"Delete Error: {str(e)}")
            return None
    
    def count(self, table: str, filters: dict = None):
        """COUNT rows"""
        try:
            query = self.client.table(table).select("*", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.count if response else 0
        except Exception as e:
            print(f"Count Error: {str(e)}")
            return 0

# Singleton instance
db = SupabaseDB()
