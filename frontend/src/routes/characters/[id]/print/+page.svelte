<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import Markdown from '$lib/components/shared/Markdown.svelte';

  const characterId = $page.params.id;

  let character = null;
  let inventory = [];
  let spellData = null;
  let loading = true;
  let error = '';

  const ARCANE = new Set(['Magic-User', 'Illusionist']);
  const DIVINE = new Set(['Cleric', 'Druid']);

  const abilities = [
    { key: 'strength', label: 'STR' },
    { key: 'intelligence', label: 'INT' },
    { key: 'wisdom', label: 'WIS' },
    { key: 'dexterity', label: 'DEX' },
    { key: 'constitution', label: 'CON' },
    { key: 'charisma', label: 'CHA' },
  ];

  const saveLabels = {
    death: 'Death/Poison',
    wands: 'Wands',
    paralyze: 'Paralysis/Stone',
    breath: 'Breath Attacks',
    spells: 'Spells/Rods/Staves',
  };

  const ordinals = ['1st', '2nd', '3rd', '4th', '5th', '6th'];

  const coinLabels = [
    { key: 'copper', abbr: 'CP' },
    { key: 'silver', abbr: 'SP' },
    { key: 'electrum', abbr: 'EP' },
    { key: 'gold', abbr: 'GP' },
    { key: 'platinum', abbr: 'PP' },
  ];

  $: className = character?.character_class?.name ?? character?.combat_stats?.monster_name ?? '';
  $: isCaster = ARCANE.has(className) || DIVINE.has(className);
  $: isPC = character?.character_type === 'pc';

  // --- Class Skills ---
  const skillLabels = {
    climb_surface: 'Climb Surfaces',
    find_traps: 'Find/Remove Traps',
    hear_noise: 'Hear Noise',
    hide_shadows: 'Hide in Shadows',
    move_silent: 'Move Silently',
    open_locks: 'Open Locks',
    pick_pockets: 'Pick Pockets',
    falling: 'Falling',
    tightrope_walking: 'Tightrope Walking',
    assassination: 'Assassination',
    agile_fighting: 'Agile Fighting',
    hide_undergrowth: 'Hide in Undergrowth',
    lay_on_hands: 'Lay on Hands',
    tracking: 'Tracking',
  };

  function formatSkill(key, value) {
    if (key === 'hear_noise') return `${value}-in-6`;
    return `${value}%`;
  }

  $: classData = character?.character_class?.class_data ?? {};
  $: levelIndex = Math.max(0, (character?.level ?? 1) - 1);
  $: visibleSkills = Object.entries(skillLabels).filter(([key]) => {
    const arr = classData.thief_skills?.[key];
    if (!Array.isArray(arr)) return false;
    const val = arr[Math.min(levelIndex, arr.length - 1)] ?? 0;
    if (key === 'hear_noise') return val > 1;
    return val > 0;
  });
  $: hasClassSkills = visibleSkills.length > 0;

  // --- Equipped Weapons ---
  $: equippedWeapons = character?.equipped_weapons ?? [];

  // --- Equipment Summary (equipped slots from inventory) ---
  $: equippedSlots = inventory
    .filter(e => e.slot)
    .map(e => ({ slot: e.slot, name: e.item?.name ?? 'Unknown' }));

  // --- Encumbrance ---
  $: totalWeight = inventory.reduce((sum, e) => {
    const w = e.item?.item_metadata?.weight ?? 0;
    return sum + w * (e.quantity ?? 1);
  }, 0);
  $: coinWeight = (
    (character?.copper ?? 0) +
    (character?.silver ?? 0) +
    (character?.electrum ?? 0) +
    (character?.gold ?? 0) +
    (character?.platinum ?? 0)
  );
  $: totalEncumbrance = totalWeight + coinWeight;

  // --- Movement formatting ---
  $: effectiveMovement = character?.combat_stats?.effective_movement ?? character?.movement_rate;
  $: movementDisplay = effectiveMovement != null
    ? `${effectiveMovement}' (${Math.floor(effectiveMovement / 3)}')`
    : (character?.movement_rate ?? '?');

  // --- Currency ---
  $: hasCoins = coinLabels.some(c => (character?.[c.key] ?? 0) > 0);

  // --- Retainers / Mercenaries / Specialists ---
  $: retainers = character?.retainers ?? [];
  $: mercenaries = character?.mercenaries ?? [];
  $: specialists = character?.specialists ?? [];
  $: maxRetainers = character?.modifiers?.charisma?.max_retainers ?? 4;
  $: totalMercCost = mercenaries.reduce((s, m) => s + (m.total_cost ?? 0), 0);
  $: totalSpecWage = specialists.reduce((s, sp) => s + (sp.wage ?? 0), 0);

  // --- Spells: group spellbook by level ---
  $: spellbookByLevel = (() => {
    if (!spellData?.spellbook?.length) return {};
    const grouped = {};
    for (const spell of spellData.spellbook) {
      const lvl = spell.level ?? 1;
      if (!grouped[lvl]) grouped[lvl] = [];
      grouped[lvl].push(spell);
    }
    return grouped;
  })();

  // --- Spells: memorized slot usage per level ---
  function memorizedByLevel(level) {
    if (!spellData) return [];
    return spellData.memorized.filter((m) => m.spell_level === ordinals.indexOf(level) + 1);
  }

  function slotUsageForLevel(levelNum) {
    if (!spellData) return null;
    const memorized = spellData.memorized.filter(m => m.spell_level === levelNum);
    const slots = spellData.slots?.[levelNum] ?? memorized.length;
    if (slots === 0 && memorized.length === 0) return null;
    return { used: memorized.length, total: slots };
  }

  onMount(async () => {
    try {
      character = await api.get(`/characters/${characterId}`);
      inventory = await api.get(`/characters/${characterId}/items`);
      if (isCaster || ARCANE.has(character.character_class?.name ?? '') || DIVINE.has(character.character_class?.name ?? '')) {
        try {
          spellData = await api.get(`/characters/${characterId}/spells`);
        } catch {
          spellData = null;
        }
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  const modifierLabels = {
    melee_adj: 'Melee',
    open_doors: 'Open Doors',
    additional_languages: 'Languages',
    literate: 'Literate',
    magic_saves: 'Magic Saves',
    ac_adj: 'AC',
    missile_adj: 'Missile',
    initiative_adj: 'Initiative',
    hp_modifier: 'HP',
    npc_reactions: 'Reactions',
    max_retainers: 'Max Retainers',
    retainer_loyalty: 'Loyalty',
  };

  const absoluteKeys = new Set(['max_retainers', 'retainer_loyalty']);

  function getModsForAbility(key) {
    if (!character?.modifiers) return {};
    const raw = character.modifiers[key];
    if (!raw || typeof raw !== 'object') return {};
    const result = {};
    for (const [k, v] of Object.entries(raw)) {
      const label = modifierLabels[k] || k;
      result[label] = absoluteKeys.has(k) ? String(v) : v;
    }
    return result;
  }

  function weaponDamageDisplay(w) {
    let dmg = w.damage_dice ?? '?';
    if (w.damage_mod > 0) dmg += `+${w.damage_mod}`;
    else if (w.damage_mod < 0) dmg += `${w.damage_mod}`;
    return dmg;
  }

  function slotLabel(slot) {
    if (!slot) return '';
    return slot.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }
</script>

<svelte:head>
  <title>{character?.name ?? 'Character'} — Print — OSE Sheet</title>
</svelte:head>

<div class="min-h-screen bg-parchment print:bg-white print:text-black">
  <!-- Print toolbar (hidden when printing) -->
  <div class="print:hidden bg-ink text-parchment-50 px-4 py-2 flex items-center justify-between">
    <span class="font-serif">Print Preview — {character?.name ?? ''}</span>
    <div class="flex gap-3">
      <button class="btn text-xs" on:click={() => window.print()}>Print</button>
      <a href="/characters/{characterId}" class="btn-ghost text-xs">← Back</a>
    </div>
  </div>

  {#if loading}
    <div class="max-w-4xl mx-auto p-8">
      <p class="text-ink-faint">Loading…</p>
    </div>
  {:else if error}
    <div class="max-w-4xl mx-auto p-8">
      <p class="text-red-700">{error}</p>
    </div>
  {:else if character}
    <div class="max-w-[800px] mx-auto p-8 print:p-4 space-y-6">

      <!-- 1. Header -->
      <div class="border-b-2 border-ink pb-3">
        <h1 class="font-serif text-4xl text-ink print:text-black">{character.name}</h1>
        <p class="text-ink-faint print:text-gray-500 mt-1">
          {character.character_class?.name ?? character.combat_stats?.monster_name ?? 'Unknown'} · Level {character.level} · {character.alignment ?? 'Neutral'}
          · XP: {character.xp ?? 0}
        </p>
      </div>

      <!-- 2. Fallen Banner -->
      {#if character.is_alive === false}
        <div class="text-center border border-gray-400 rounded py-2 mb-4">
          <span class="font-serif text-lg tracking-widest uppercase text-gray-500">☠ Fallen ☠</span>
        </div>
      {/if}

      <!-- 3. Two column: Combat + Saves -->
      <div class="grid grid-cols-2 gap-6">
        <!-- Combat Stats -->
        <div>
          <h2 class="section-title print:text-black">Combat</h2>
          <table class="w-full text-sm">
            <tbody>
              <tr class="border-b border-parchment-200 print:border-gray-200">
                <td class="py-1 text-ink-faint print:text-gray-500">HP</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">
                  {character.hp_current ?? '?'} / {character.hp_max ?? '?'}
                </td>
              </tr>
              <tr class="border-b border-parchment-200 print:border-gray-200">
                <td class="py-1 text-ink-faint print:text-gray-500">Armor Class</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">{character.ac ?? '?'}</td>
              </tr>
              {#if character.rear_ac != null}
                <tr class="border-b border-parchment-200 print:border-gray-200">
                  <td class="py-1 text-ink-faint print:text-gray-500">Rear AC</td>
                  <td class="py-1 font-medium text-ink print:text-black text-right">{character.rear_ac}</td>
                </tr>
              {/if}
              {#if character.shieldless_ac != null}
                <tr class="border-b border-parchment-200 print:border-gray-200">
                  <td class="py-1 text-ink-faint print:text-gray-500">Shieldless AC</td>
                  <td class="py-1 font-medium text-ink print:text-black text-right">{character.shieldless_ac}</td>
                </tr>
              {/if}
              <tr class="border-b border-parchment-200 print:border-gray-200">
                <td class="py-1 text-ink-faint print:text-gray-500">THAC0</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">{character.thac0 ?? '?'}</td>
              </tr>
              <tr>
                <td class="py-1 text-ink-faint print:text-gray-500">Movement</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">{movementDisplay}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Saving Throws -->
        {#if character.saving_throws}
          <div>
            <h2 class="section-title print:text-black">Saving Throws</h2>
            <table class="w-full text-sm">
              <tbody>
                {#each Object.entries(saveLabels) as [key, label]}
                  <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                    <td class="py-1 text-ink-faint print:text-gray-500">{label}</td>
                    <td class="py-1 font-medium text-ink print:text-black text-right">
                      {character.saving_throws[key] ?? '—'}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <!-- 4. Equipped Weapons -->
      {#if equippedWeapons.length > 0}
        <div>
          <h2 class="section-title print:text-black">Equipped Weapons</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Weapon</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Range</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">THAC0</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Damage</th>
              </tr>
            </thead>
            <tbody>
              {#each equippedWeapons as w}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">
                    {w.name}
                    {#if w.dual_wield_penalty}
                      <span class="text-xs text-ink-faint print:text-gray-500">(-{w.dual_wield_penalty})</span>
                    {/if}
                  </td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{w.range ?? 'Melee'}</td>
                  <td class="py-1 font-medium text-ink print:text-black text-right">{w.effective_thac0 ?? '?'}</td>
                  <td class="py-1 font-medium text-ink print:text-black text-right">
                    {weaponDamageDisplay(w)}
                    {#if w.weapon_type === 'ranged' && w.ammo_name}
                      <span class="text-xs text-ink-faint print:text-gray-500 ml-1">({w.ammo_name}: {w.ammo_count ?? '?'})</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <!-- 5. Ability Scores -->
      <div>
        <h2 class="section-title print:text-black">Ability Scores</h2>
        <div class="grid grid-cols-3 sm:grid-cols-6 gap-3">
          {#each abilities as { key, label }}
            {@const mods = getModsForAbility(key)}
            <div class="border border-ink-faint print:border-gray-300 rounded-sm p-2 text-center">
              <div class="text-xs text-ink-faint print:text-gray-500 uppercase">{label}</div>
              <div class="font-serif text-2xl text-ink print:text-black">{character[key] ?? 10}</div>
              {#each Object.entries(mods) as [mod, val]}
                <div class="text-xs text-ink-light print:text-gray-600">
                  {mod}: {val > 0 ? `+${val}` : val}
                </div>
              {/each}
            </div>
          {/each}
        </div>
      </div>

      <!-- 6. Equipment Summary + Encumbrance -->
      {#if equippedSlots.length > 0 || totalEncumbrance > 0}
        <div>
          <h2 class="section-title print:text-black">Equipment</h2>
          {#if equippedSlots.length > 0}
            <div class="text-sm text-ink print:text-black mb-2">
              {#each equippedSlots as { slot, name }, i}
                <span class="text-ink-faint print:text-gray-500">{slotLabel(slot)}:</span> {name}{#if i < equippedSlots.length - 1}<span class="text-ink-faint print:text-gray-400 mx-2">|</span>{/if}
              {/each}
            </div>
          {/if}
          <div class="text-xs text-ink-faint print:text-gray-500">
            Encumbrance: {totalEncumbrance} / 1,600 coins
            {#if totalEncumbrance > 1600}
              <span class="text-red-700 font-medium print:text-red-700"> — Overloaded!</span>
            {/if}
          </div>
        </div>
      {/if}

      <!-- 7. Full Inventory -->
      {#if inventory.length > 0}
        <div>
          <h2 class="section-title print:text-black">Inventory</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Item</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Type</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Slot</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Wt.</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Qty</th>
              </tr>
            </thead>
            <tbody>
              {#each inventory as entry}
                {@const item = entry.item}
                {@const displayName = (!entry.identified && item?.unidentified_name) ? item.unidentified_name : (item?.name ?? 'Unknown')}
                {@const weight = item?.item_metadata?.weight ?? 0}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">
                    {displayName}
                    {#if !entry.identified && item?.unidentified_name}
                      <span class="text-xs text-ink-faint print:text-gray-500">(?)</span>
                    {/if}
                  </td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{item?.item_type ?? ''}</td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{entry.slot ? slotLabel(entry.slot) : ''}</td>
                  <td class="py-1 text-ink print:text-black text-right">{weight > 0 ? weight : ''}</td>
                  <td class="py-1 text-ink print:text-black text-right">{entry.quantity}</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="border-t border-ink-faint print:border-gray-300">
                <td colspan="3" class="py-1 text-xs text-ink-faint print:text-gray-500 text-right">Total weight:</td>
                <td class="py-1 text-xs font-medium text-ink print:text-black text-right">{totalWeight}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      {/if}

      <!-- 8. Currency -->
      {#if hasCoins}
        <div>
          <h2 class="section-title print:text-black">Currency</h2>
          <div class="flex gap-6 text-sm">
            {#each coinLabels as { key, abbr }}
              {#if (character[key] ?? 0) > 0}
                <div class="text-center">
                  <div class="text-xs text-ink-faint print:text-gray-500 uppercase">{abbr}</div>
                  <div class="font-medium text-ink print:text-black">{character[key]}</div>
                </div>
              {/if}
            {/each}
          </div>
          <div class="text-xs text-ink-faint print:text-gray-500 mt-1">
            Coin weight: {coinWeight}
          </div>
        </div>
      {/if}

      <!-- 9. Spells -->
      {#if spellData && (spellData.spellbook.length > 0 || spellData.memorized.length > 0)}
        <div>
          <h2 class="section-title print:text-black">Spells</h2>

          {#if spellData.spellbook.length > 0}
            <h3 class="text-sm font-medium text-ink print:text-black mb-2">Spellbook</h3>
            {#each Object.entries(spellbookByLevel) as [level, spells]}
              <div class="mb-2">
                <span class="text-xs text-ink-faint print:text-gray-500 font-medium">{ordinals[level - 1] ?? `${level}th`} Level:</span>
                <span class="flex flex-wrap gap-1 mt-0.5">
                  {#each spells as spell}
                    <span class="text-xs border border-ink-faint print:border-gray-300 rounded px-2 py-0.5">
                      {spell.name}
                    </span>
                  {/each}
                </span>
              </div>
            {/each}
          {/if}

          {#if spellData.memorized.length > 0}
            <h3 class="text-sm font-medium text-ink print:text-black mb-2 mt-3">Memorized</h3>
            <div class="space-y-1">
              {#each ordinals as level, idx}
                {@const memorized = memorizedByLevel(level)}
                {@const usage = slotUsageForLevel(idx + 1)}
                {#if memorized.length > 0}
                  <div class="flex gap-2 items-baseline">
                    <span class="text-xs text-ink-faint print:text-gray-500 w-12 shrink-0">
                      {level}
                      {#if usage}
                        <span class="text-[10px]">({usage.used}/{usage.total})</span>
                      {/if}
                    </span>
                    <div class="flex flex-wrap gap-2">
                      {#each memorized as entry}
                        <span class="text-xs border border-ink-faint print:border-gray-300 rounded px-2 py-0.5"
                          class:opacity-50={entry.cast}
                          class:line-through={entry.cast}
                        >
                          {entry.spell.name}
                        </span>
                      {/each}
                    </div>
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- 10. Class Skills -->
      {#if hasClassSkills}
        <div>
          <h2 class="section-title print:text-black">Class Skills</h2>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {#each visibleSkills as [key, label]}
              {@const arr = classData.thief_skills[key]}
              {@const val = arr[Math.min(levelIndex, arr.length - 1)] ?? 0}
              <div class="border border-ink-faint print:border-gray-300 rounded-sm p-2 text-center">
                <div class="text-xs text-ink-faint print:text-gray-500 uppercase">{label}</div>
                <div class="font-serif text-xl text-ink print:text-black">{formatSkill(key, val)}</div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- 11. Class Abilities -->
      {#if classData.abilities && Object.keys(classData.abilities).length > 0}
        <div>
          <h2 class="section-title print:text-black">Class Abilities</h2>
          <ul class="space-y-1">
            {#each Object.entries(classData.abilities) as [name, desc]}
              <li class="text-sm text-ink print:text-black">
                <strong>{name}:</strong>
                <Markdown text={desc} />
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- 12. Retainers (PC only) -->
      {#if isPC && retainers.length > 0}
        <div>
          <h2 class="section-title print:text-black">Retainers ({retainers.length} / {maxRetainers})</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Name</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Class</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Lvl</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">HP</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">AC</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Loyalty</th>
              </tr>
            </thead>
            <tbody>
              {#each retainers as r}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">{r.name}</td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{r.character_class_name ?? 'Monster'}</td>
                  <td class="py-1 text-ink print:text-black text-right">{r.level}</td>
                  <td class="py-1 text-ink print:text-black text-right">{r.hp_current}/{r.hp_max}</td>
                  <td class="py-1 text-ink print:text-black text-right">{r.ac}</td>
                  <td class="py-1 text-ink print:text-black text-right">{r.loyalty ?? '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <!-- 13. Mercenaries (PC only) -->
      {#if isPC && mercenaries.length > 0}
        <div>
          <h2 class="section-title print:text-black">Mercenaries</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Type</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Race</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Qty</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">AC</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Morale</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Cost/mo</th>
              </tr>
            </thead>
            <tbody>
              {#each mercenaries as m}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">{m.name ?? m.merc_type}</td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{m.race ?? '—'}</td>
                  <td class="py-1 text-ink print:text-black text-right">{m.quantity}</td>
                  <td class="py-1 text-ink print:text-black text-right">{m.ac ?? '—'}</td>
                  <td class="py-1 text-ink print:text-black text-right">{m.morale ?? '—'}</td>
                  <td class="py-1 text-ink print:text-black text-right">{m.total_cost ?? '—'} gp</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="border-t border-ink-faint print:border-gray-300">
                <td colspan="5" class="py-1 text-xs text-ink-faint print:text-gray-500 text-right">Total monthly cost:</td>
                <td class="py-1 text-xs font-medium text-ink print:text-black text-right">{totalMercCost} gp</td>
              </tr>
            </tfoot>
          </table>
        </div>
      {/if}

      <!-- 14. Specialists (PC only) -->
      {#if isPC && specialists.length > 0}
        <div>
          <h2 class="section-title print:text-black">Specialists</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Type</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Task</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Wage/mo</th>
              </tr>
            </thead>
            <tbody>
              {#each specialists as sp}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">{sp.name ?? sp.spec_type}</td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{sp.task ?? '—'}</td>
                  <td class="py-1 text-ink print:text-black text-right">{sp.wage ?? '—'} gp</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="border-t border-ink-faint print:border-gray-300">
                <td colspan="2" class="py-1 text-xs text-ink-faint print:text-gray-500 text-right">Total monthly wages:</td>
                <td class="py-1 text-xs font-medium text-ink print:text-black text-right">{totalSpecWage} gp</td>
              </tr>
            </tfoot>
          </table>
        </div>
      {/if}

      <!-- 15. Notes -->
      {#if character.notes}
        <div>
          <h2 class="section-title print:text-black">Notes</h2>
          <p class="text-sm text-ink print:text-black whitespace-pre-wrap">{character.notes}</p>
        </div>
      {/if}

    </div>
  {/if}
</div>

<style>
  @media print {
    :global(body) {
      background: white;
    }
  }
</style>
