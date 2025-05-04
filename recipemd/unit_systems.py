"""
Provides predefined instances of :class:`recipemd.units.UnitSystem` for different languages
"""


from recipemd._unit_systems._en_us import en_us
from recipemd._unit_systems._en_us_si import en_us_si
from recipemd._unit_systems._de import de



en_us = en_us
"""
A unit system for US English, using US customary units for display.

:meta hide-value:
"""

en_us_si = en_us_si
"""
Variant of :const:`en_us`, using SI units for display.

:meta hide-value:
"""

de = de
"""
A unit system for German.

:meta hide-value:
"""


en = en_us
"""
Shortcut for :const:`en_us`

:meta hide-value:
"""




