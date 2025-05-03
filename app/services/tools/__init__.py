# Import tools modules with implementations
from app.services.tools import registry
from app.services.tools import vector_search

# No need to manually register tools anymore as they self-register with the enhanced decorator
