# ratatosk/providers/__init__.py
from .ratatosk import RatatoskProvider

# L'unique objet que le reste du backend importe
provider = RatatoskProvider()

__all__ = ["RatatoskProvider", "provider"]
