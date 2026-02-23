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

  $: className = character?.character_class?.name ?? '';
  $: isCaster = ARCANE.has(className) || DIVINE.has(className);

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

  function memorizedByLevel(level) {
    if (!spellData) return [];
    return spellData.memorized.filter((m) => m.spell_level === ordinals.indexOf(level) + 1);
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

      <!-- Header -->
      <div class="border-b-2 border-ink pb-3">
        <h1 class="font-serif text-4xl text-ink print:text-black">{character.name}</h1>
        <p class="text-ink-faint print:text-gray-500 mt-1">
          {character.character_class?.name ?? 'Unknown'} · Level {character.level} · {character.alignment ?? 'Neutral'}
          · XP: {character.xp ?? 0}
        </p>
      </div>

      {#if character.is_alive === false}
        <div class="text-center border border-gray-400 rounded py-2 mb-4">
          <span class="font-serif text-lg tracking-widest uppercase text-gray-500">☠ Fallen ☠</span>
        </div>
      {/if}

      <!-- Two column: Combat + Saves -->
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
              <tr class="border-b border-parchment-200 print:border-gray-200">
                <td class="py-1 text-ink-faint print:text-gray-500">THAC0</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">{character.thac0 ?? '?'}</td>
              </tr>
              <tr>
                <td class="py-1 text-ink-faint print:text-gray-500">Movement</td>
                <td class="py-1 font-medium text-ink print:text-black text-right">{character.movement_rate ?? '?'}</td>
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

      <!-- Ability Scores -->
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

      <!-- Inventory -->
      {#if inventory.length > 0}
        <div>
          <h2 class="section-title print:text-black">Inventory</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint print:border-gray-300">
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Item</th>
                <th class="text-left py-1 text-ink-faint print:text-gray-500 font-normal">Type</th>
                <th class="text-right py-1 text-ink-faint print:text-gray-500 font-normal">Qty</th>
              </tr>
            </thead>
            <tbody>
              {#each inventory as entry}
                <tr class="border-b border-parchment-200 print:border-gray-200 last:border-0">
                  <td class="py-1 text-ink print:text-black">{entry.item.name}</td>
                  <td class="py-1 text-ink-faint print:text-gray-500">{entry.item.item_type}</td>
                  <td class="py-1 text-ink print:text-black text-right">{entry.quantity}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <!-- Currency -->
      {#if character.character_metadata}
        {@const meta = character.character_metadata}
        {#if (meta.cp || meta.sp || meta.ep || meta.gp || meta.pp)}
          <div>
            <h2 class="section-title print:text-black">Currency</h2>
            <div class="flex gap-6 text-sm">
              {#each ['cp', 'sp', 'ep', 'gp', 'pp'] as c}
                {#if meta[c]}
                  <div class="text-center">
                    <div class="text-xs text-ink-faint print:text-gray-500 uppercase">{c}</div>
                    <div class="font-medium text-ink print:text-black">{meta[c]}</div>
                  </div>
                {/if}
              {/each}
            </div>
          </div>
        {/if}
      {/if}

      <!-- Spells -->
      {#if spellData && (spellData.spellbook.length > 0 || spellData.memorized.length > 0)}
        <div>
          <h2 class="section-title print:text-black">Spells</h2>

          {#if spellData.spellbook.length > 0}
            <h3 class="text-sm font-medium text-ink print:text-black mb-2">Spellbook</h3>
            <div class="flex flex-wrap gap-2 mb-4">
              {#each spellData.spellbook as spell}
                <span class="text-xs border border-ink-faint print:border-gray-300 rounded px-2 py-0.5">
                  {spell.name} (Lvl {spell.level})
                </span>
              {/each}
            </div>
          {/if}

          {#if spellData.memorized.length > 0}
            <h3 class="text-sm font-medium text-ink print:text-black mb-2">Memorized</h3>
            <div class="space-y-1">
              {#each ordinals as level}
                {@const memorized = memorizedByLevel(level)}
                {#if memorized.length > 0}
                  <div class="flex gap-2 items-baseline">
                    <span class="text-xs text-ink-faint print:text-gray-500 w-8">{level}</span>
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

      <!-- Class Skills -->
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

      <!-- Class Abilities -->
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

      <!-- Notes -->
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
