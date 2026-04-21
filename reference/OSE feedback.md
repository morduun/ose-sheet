## OSE feedback

### Barry

- [x] I think I did find a weird thing, if I fire it does change my inventory but then if I add arrows back i have to unequip/equip to get it to update
- [x] idk if you care but it does allow you to equip a two-handed weapon and a weapon in the off hand
- [x] how do you normally denote whether or not a waterskin has water in it or not?
- [x] just noticed now that I have more items, every time I hit +1 on something it does a quick refresh and pulls you back to the top of the screen, so turning that quantity into an editable text field would be handy
- [x] Also for consideration, being able to sort items into bags/backpacks



## Claude

- [x] Item editor doesn't expose fillable or capacity
  GMs can't mark items as fillable or set container capacity from the UI — requires DB edits. The ItemForm.svelte needs a fillable checkbox and
    capacity number field added to the metadata section.

- [x] Stash doesn't preserve container/state data
  Taking items from stash or returning them loses container_item_id, dropped, and state (fill level). A backpack's contents association is
    destroyed on stash round-trip.
- [x] Can equip items from inside dropped containers
  No validation prevents equipping a sword that's inside your dropped backpack 50 feet behind you.

- [x] Print page doesn't show container grouping or fill state
  Inventory prints as a flat list — no container hierarchy, no fill indicators.

- [x] Character creation doesn't auto-populate HP
  Saving throws, THAC0, and AC are auto-populated from class data, but HP isn't rolled/set from the class hit die. No starting equipment
    assignment either.

- [x] No generic Flask item in seed data
  Only the throwable "Flask, Oil" exists. No plain fillable flask for players to fill with whatever they want.

- [x] Admin content management is minimal
  Admin page only has backups and allowlist. No UI to manage default items, spells, or classes from the admin panel (though these are editable
    via the existing /items, /spells, /classes pages).

## Finch

- [x] Vehicles
- [ ] 
