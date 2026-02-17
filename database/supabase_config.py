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
        if self._client is None:
            self._client = create_client(
                Config.SUPABASE_URL,
                Config.SUPABASE_KEY
            )
    
    @property
    def client(self) -> Client:
        """Get Supabase client"""
        if self._client is None:
            self._client = create_client(
                Config.SUPABASE_URL,
                Config.SUPABASE_KEY
            )
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
