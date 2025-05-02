# Services module
from app.services.supabase import get_supabase_client, supabase_client
from app.services.function_calling import function_calling

__all__ = ["get_supabase_client", "supabase_client", "function_calling"] 