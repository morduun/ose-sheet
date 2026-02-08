# OSE SHEETS: Concept

> _OSE Sheets is a simple library for OSE characters. OSE doesn't really have a 'Beyond' site, nor does it need all the wild bells and whistles, but an online repository of both live characters and a graveyard of the fallen does help immensely, especially for online campaigns._

## INTERFACE

- Simple web interface
- Requires Google Login
- GM can create multiple campaigns and give their players a URL to log in to.
- Players can create multiple characters with a campaign identifier.
  - Players can input their attributes and select their class as a drop-down.
  - Parts of the sheet will auto-populate based on Class (hit die type, attack matrix, saving throws, spells memorizable)
- Both Players and GMs can view and modify character sheets.
- GMs can also create item cards, with two descriptions: player visible and gm-visible. Both can be edited. 
  - Items also contain metadata as defined by the item type (armor can take armor type and AC; weapon can take weapon type, hit bonus, damage bonus, damage dice, and range; jewelry take gp value & materials, and so forth)
- Players can be assigned item cards
- Item cards can also go into a 'campaign pool' where they lie unclaimed but claimable by players. 
- Default item cards for all mundane equipment are available by default for all characters.
- Characters can maintain an inventory of items.
- Characters can also maintain a count of their coins of all coin types (copper, silver, electrum, gold, platinum)
- Spellcasting characters can maintain a "Spellbook" of spells they have been able to add to their spellbook. 
  - The interface allows tabs across spell levels for easy viewing; there are **six** levels.
  - The interface allows adding from a drop-down of all extant spells from a given level when a spellbook page is open.

## REFERENCE

- PDF files in the /reference directory of the repo express the intent if not the format of the character sheet functionality.
  - "Character Sheet.pdf" has the bulk of the desirable items to display for a character, though it misses specific areas to write additional details for attribute modifiers.
  - "Stonehell.webp" fills in the blanks for attributes that Character Sheet doesn't possess.
  - "Spell Lists.pdf" has a complete spell list for all spells for all four casting classes.