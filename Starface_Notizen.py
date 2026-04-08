"""Entry point for Starface phone system integration."""

# In Starface ausfuehren mit "c:\Users\<username>\Starface_anrufe\anrufe.py" $(callerid)

import sys

from src.starface_notifier import main

sys.exit(main())
