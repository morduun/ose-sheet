<script>
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';

  const campaignId = $page.params.id;

  let campaign = null;
  let characters = [];
  let loading = true;
  let error = '';
  let userId = null;
  let pollTimer = null;

  // localStorage-backed state
  let initiatives = {};
  let conditions = {};  // { [charId]: [{name: string, turns: number|null}] }

  // Encounter tracker state
  let encounterActive = false;
  let encounterRound = 1;
  let activeCharIndex = 0;  // index into sortedCharacters

  // HP edit state
  let hpEditId = null;
  let hpDelta = '';
  let savingHP = false;

  // Condition input state (per-character)
  let conditionInputs = {};

  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch {
      return null;
    }
  }

  $: isGM = campaign && userId && campaign.gm_id === userId;
  $: if (browser && campaign && !isGM) goto(`/campaigns/${campaignId}`);

  // When encounter is active, always sort by initiative
  $: sortedCharacters = encounterActive || Object.keys(initiatives).length > 0
    ? [...characters].sort((a, b) => {
        const ai = initiatives[a.id] ?? 999;
        const bi = initiatives[b.id] ?? 999;
        return bi - ai || a.name.localeCompare(b.name);
      })
    : [...characters].sort((a, b) => a.name.localeCompare(b.name));

  $: activeCharId = encounterActive && sortedCharacters.length > 0
    ? sortedCharacters[activeCharIndex % sortedCharacters.length]?.id
    : null;

  // --- localStorage ---

  function loadLocalState() {
    try {
      initiatives = JSON.parse(localStorage.getItem(`referee_initiative_${campaignId}`)) || {};
    } catch {
      initiatives = {};
    }
    try {
      conditions = JSON.parse(localStorage.getItem(`referee_conditions_${campaignId}`)) || {};
    } catch {
      conditions = {};
    }
    try {
      const enc = JSON.parse(localStorage.getItem(`referee_encounter_${campaignId}`));
      if (enc) {
        encounterActive = enc.active || false;
        encounterRound = enc.round || 1;
        activeCharIndex = enc.currentIndex || 0;
      }
    } catch {
      // defaults
    }
  }

  function saveInitiatives() {
    localStorage.setItem(`referee_initiative_${campaignId}`, JSON.stringify(initiatives));
  }

  function saveConditions() {
    localStorage.setItem(`referee_conditions_${campaignId}`, JSON.stringify(conditions));
  }

  function saveEncounter() {
    localStorage.setItem(`referee_encounter_${campaignId}`, JSON.stringify({
      active: encounterActive,
      round: encounterRound,
      currentIndex: activeCharIndex,
    }));
  }

  function cleanupLocalState() {
    const ids = new Set(characters.map(c => String(c.id)));
    let changed = false;
    for (const key of Object.keys(initiatives)) {
      if (!ids.has(key)) { delete initiatives[key]; changed = true; }
    }
    for (const key of Object.keys(conditions)) {
      if (!ids.has(key)) { delete conditions[key]; changed = true; }
    }
    if (changed) {
      saveInitiatives();
      saveConditions();
    }
    // Clamp activeCharIndex if characters changed
    if (encounterActive && activeCharIndex >= sortedCharacters.length) {
      activeCharIndex = 0;
      saveEncounter();
    }
  }

  // --- Data fetching ---

  async function fetchRefereeData() {
    try {
      const data = await api.get(`/campaigns/${campaignId}/referee`);
      characters = data;
      cleanupLocalState();
    } catch (e) {
      if (loading) error = e.message;
    }
  }

  onMount(async () => {
    userId = getUserId();
    loadLocalState();
    try {
      campaign = await api.get(`/campaigns/${campaignId}`);
    } catch (e) {
      error = e.message;
      loading = false;
      return;
    }
    await fetchRefereeData();
    loading = false;
    pollTimer = setInterval(fetchRefereeData, 5000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
  });

  // --- HP ---

  function hpPct(c) {
    return c.hp_max > 0 ? Math.round((c.hp_current / c.hp_max) * 100) : 0;
  }

  function hpColor(c) {
    const pct = hpPct(c);
    if (pct <= 25) return 'text-red-800 font-bold';
    if (pct <= 50) return 'text-amber-700';
    return 'text-green-800';
  }

  function startHPEdit(charId) {
    hpEditId = charId;
    hpDelta = '';
  }

  function handleHPKeydown(e, char) {
    if (e.key === 'Enter') submitHP(char);
    if (e.key === 'Escape') { hpEditId = null; hpDelta = ''; }
  }

  async function submitHP(char) {
    const val = parseInt(hpDelta);
    if (isNaN(val) || val === 0) {
      hpEditId = null;
      hpDelta = '';
      return;
    }
    savingHP = true;
    const newCurrent = Math.max(0, Math.min(char.hp_max, char.hp_current + val));
    char.hp_current = newCurrent;
    characters = characters;
    hpEditId = null;
    hpDelta = '';
    try {
      await api.patch(`/characters/${char.id}`, { hp_current: newCurrent });
    } catch {
      // Poll will correct
    } finally {
      savingHP = false;
    }
  }

  // --- Weapons ---

  function formatWeapon(w) {
    let dmg = w.damage_dice;
    if (w.damage_mod > 0) dmg += `+${w.damage_mod}`;
    else if (w.damage_mod < 0) dmg += `${w.damage_mod}`;
    let line = `${w.name}: THAC0 ${w.effective_thac0}, ${dmg}`;
    if (w.weapon_type === 'ranged' && w.ammo_name) {
      line += ` (${w.ammo_name}: ${w.ammo_count ?? '?'})`;
    }
    return line;
  }

  // --- Initiative ---

  function handleInitChange(charId, value) {
    const num = parseInt(value);
    if (isNaN(num)) {
      delete initiatives[charId];
    } else {
      initiatives[charId] = num;
    }
    initiatives = initiatives;
    saveInitiatives();
  }

  // --- Conditions ---

  function addCondition(charId, input) {
    const raw = (input || '').trim();
    if (!raw) return;

    // Parse "name-N" format for turns, but be careful with hyphenated names
    // Only treat trailing -NUMBER as turns
    const match = raw.match(/^(.+?)-(\d+)$/);
    let name, turns;
    if (match) {
      name = match[1].trim();
      turns = parseInt(match[2]);
    } else {
      name = raw;
      turns = null;
    }

    if (!name) return;

    const list = conditions[charId] || [];
    list.push({ name, turns });
    conditions[charId] = list;
    conditions = conditions;
    saveConditions();

    // Clear input
    conditionInputs[charId] = '';
    conditionInputs = conditionInputs;
  }

  function removeCondition(charId, index) {
    const list = conditions[charId] || [];
    list.splice(index, 1);
    conditions[charId] = list;
    conditions = conditions;
    saveConditions();
  }

  function handleConditionKeydown(e, charId) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addCondition(charId, conditionInputs[charId]);
    }
  }

  // --- Encounter Tracker ---

  function startEncounter() {
    encounterActive = true;
    encounterRound = 1;
    activeCharIndex = 0;
    saveEncounter();
  }

  function endEncounter() {
    encounterActive = false;
    encounterRound = 1;
    activeCharIndex = 0;
    saveEncounter();
  }

  function nextTurn() {
    if (!encounterActive || sortedCharacters.length === 0) return;

    const nextIndex = activeCharIndex + 1;

    if (nextIndex >= sortedCharacters.length) {
      // Wrap around — new round
      activeCharIndex = 0;
      encounterRound += 1;
      tickDownConditions();
    } else {
      activeCharIndex = nextIndex;
    }
    saveEncounter();
  }

  function prevTurn() {
    if (!encounterActive || sortedCharacters.length === 0) return;

    if (activeCharIndex > 0) {
      activeCharIndex -= 1;
    } else if (encounterRound > 1) {
      // Wrap back to end of previous round (no tick-up — that would be confusing)
      activeCharIndex = sortedCharacters.length - 1;
      encounterRound -= 1;
    }
    saveEncounter();
  }

  function tickDownConditions() {
    let changed = false;
    for (const charId of Object.keys(conditions)) {
      const list = conditions[charId];
      if (!list || !list.length) continue;
      for (let i = list.length - 1; i >= 0; i--) {
        if (list[i].turns != null) {
          list[i].turns -= 1;
          changed = true;
          if (list[i].turns <= 0) {
            list.splice(i, 1);
          }
        }
      }
      conditions[charId] = list;
    }
    if (changed) {
      conditions = conditions;
      saveConditions();
    }
  }
</script>

<svelte:head>
  <title>Referee Panel — {campaign?.name ?? 'Campaign'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading...</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if campaign}
  <PageWrapper title="Referee Panel" maxWidth="max-w-7xl">
    <!-- Header bar -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <a href="/campaigns/{campaignId}" class="text-xs text-ink-faint hover:text-ink">&larr; {campaign.name}</a>

      <div class="flex items-center gap-3">
        {#if encounterActive}
          <div class="flex items-center gap-2 panel py-1.5 px-3">
            <span class="text-xs text-ink-faint uppercase tracking-wide">Round</span>
            <span class="font-serif text-xl text-ink leading-none">{encounterRound}</span>
          </div>
          <button class="btn-ghost text-xs" on:click={prevTurn} title="Previous turn">&larr; Prev</button>
          <button class="btn text-xs" on:click={nextTurn}>Next Turn &rarr;</button>
          <button class="btn-danger text-xs" on:click={endEncounter}>End Encounter</button>
        {:else}
          <button class="btn text-xs" on:click={startEncounter}>Start Encounter</button>
        {/if}
      </div>
    </div>

    {#if characters.length === 0}
      <div class="panel text-center py-6">
        <p class="text-ink-faint text-sm">No living characters in this campaign.</p>
      </div>
    {:else}
      <div class="panel overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-ink-faint uppercase tracking-wide">
              <th class="text-center pb-2 px-2 w-16">Init</th>
              <th class="text-left pb-2 px-2">Name</th>
              <th class="text-left pb-2 px-2">Class</th>
              <th class="text-center pb-2 px-2">AC</th>
              <th class="text-center pb-2 px-2">HP</th>
              <th class="text-center pb-2 px-2">THAC0</th>
              <th class="text-left pb-2 px-2">Weapons</th>
              <th class="text-center pb-2 px-2">Move</th>
              <th class="text-left pb-2 px-2 min-w-[180px]">Conditions</th>
            </tr>
          </thead>
          <tbody>
            {#each sortedCharacters as char, idx (char.id)}
              {@const pct = hpPct(char)}
              {@const isActive = encounterActive && char.id === activeCharId}
              <tr
                class="border-t border-parchment-200 transition-colors {isActive ? 'active-turn' : 'row-hover'}"
              >
                <!-- Initiative -->
                <td class="text-center py-1.5 px-2">
                  <input
                    class="input w-14 text-center text-sm py-0.5"
                    type="number"
                    value={initiatives[char.id] ?? ''}
                    on:input={(e) => handleInitChange(char.id, e.target.value)}
                    placeholder="--"
                  />
                </td>

                <!-- Name -->
                <td class="py-1.5 px-2">
                  <a href="/characters/{char.id}" class="text-ink hover:underline font-medium">
                    {char.name}
                  </a>
                  {#if isActive}
                    <span class="text-[10px] ml-1 text-amber-700 font-medium">&bull; active</span>
                  {/if}
                </td>

                <!-- Class & Level -->
                <td class="py-1.5 px-2 text-ink-faint">
                  {char.character_class?.name ?? '?'} {char.level}
                </td>

                <!-- AC -->
                <td class="text-center py-1.5 px-2 font-serif text-lg">{char.ac ?? '?'}</td>

                <!-- HP -->
                <td class="text-center py-1.5 px-2">
                  {#if hpEditId === char.id}
                    <div class="flex items-center justify-center gap-1">
                      <input
                        class="input w-14 text-center text-sm py-0.5"
                        type="number"
                        placeholder="+/-"
                        bind:value={hpDelta}
                        on:keydown={(e) => handleHPKeydown(e, char)}
                        autofocus
                      />
                      <button class="btn text-xs px-1.5 py-0.5" on:click={() => submitHP(char)} disabled={savingHP}>OK</button>
                    </div>
                  {:else}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <span
                      class="cursor-pointer hover:bg-parchment-100 rounded px-1 font-serif text-lg {hpColor(char)}"
                      on:click={() => startHPEdit(char.id)}
                      title="Click to adjust HP"
                    >
                      {char.hp_current}/{char.hp_max}
                    </span>
                    {#if pct <= 50}
                      <div class="h-1 bg-parchment-200 rounded-full overflow-hidden mt-0.5 mx-auto w-12">
                        <div
                          class="h-full rounded-full {pct <= 25 ? 'bg-red-800' : 'bg-amber-600'}"
                          style="width: {pct}%"
                        ></div>
                      </div>
                    {/if}
                  {/if}
                </td>

                <!-- THAC0 -->
                <td class="text-center py-1.5 px-2 font-serif text-lg">{char.thac0 ?? '?'}</td>

                <!-- Weapons -->
                <td class="py-1.5 px-2">
                  {#if char.equipped_weapons?.length}
                    {#each char.equipped_weapons as w}
                      <div class="text-xs text-ink leading-snug">{formatWeapon(w)}</div>
                    {/each}
                  {:else}
                    <span class="text-xs text-ink-faint">None</span>
                  {/if}
                </td>

                <!-- Movement -->
                <td class="text-center py-1.5 px-2">{char.movement_rate ?? '?'}'</td>

                <!-- Conditions -->
                <td class="py-1.5 px-2">
                  {#if conditions[char.id]?.length}
                    <div class="flex flex-wrap gap-1 mb-1">
                      {#each conditions[char.id] as cond, ci}
                        <span class="condition-chip" class:condition-expiring={cond.turns != null && cond.turns <= 1}>
                          {cond.name}{#if cond.turns != null} <span class="condition-turns">({cond.turns})</span>{/if}
                          <!-- svelte-ignore a11y-click-events-have-key-events -->
                          <!-- svelte-ignore a11y-no-static-element-interactions -->
                          <span
                            class="condition-x"
                            on:click={() => removeCondition(char.id, ci)}
                            title="Remove condition"
                          >&times;</span>
                        </span>
                      {/each}
                    </div>
                  {/if}
                  <input
                    class="input w-full text-xs py-0.5"
                    type="text"
                    bind:value={conditionInputs[char.id]}
                    on:keydown={(e) => handleConditionKeydown(e, char.id)}
                    placeholder="name or name-turns"
                  />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </PageWrapper>
{/if}

<style>
  .active-turn {
    background-color: rgba(180, 140, 60, 0.15);
    box-shadow: inset 3px 0 0 0 rgb(180, 140, 60);
  }

  .condition-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.65rem;
    line-height: 1.4;
    padding: 0.05rem 0.4rem;
    border-radius: 0.25rem;
    background-color: var(--parchment-200, #e8dcc8);
    color: var(--ink-faint, #6b5c4a);
    white-space: nowrap;
  }

  .condition-expiring {
    background-color: rgba(153, 27, 27, 0.15);
    color: rgb(153, 27, 27);
  }

  .condition-turns {
    font-weight: 600;
  }

  .condition-x {
    cursor: pointer;
    margin-left: 0.15rem;
    font-size: 0.8rem;
    line-height: 1;
    opacity: 0.5;
  }

  .condition-x:hover {
    opacity: 1;
  }

  .row-hover:hover {
    background-color: rgba(233, 220, 195, 0.5);
  }
</style>
