<script>
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Markdown from '$lib/components/shared/Markdown.svelte';
  import DiceOverlay from '$lib/components/shared/DiceOverlay.svelte';

  const campaignId = $page.params.id;

  let campaign = null;
  let characters = [];
  let loading = true;
  let error = '';
  let userId = null;
  let pollTimer = null;

  // localStorage-backed state
  let initiatives = {};
  let conditions = {};  // { [combatantId]: [{name: string, turns: number|null}] }

  // Encounter tracker state
  let encounterActive = false;
  let encounterRound = 1;
  let activeCombatantIndex = 0;

  // HP edit state
  let hpEditId = null;
  let hpDelta = '';
  let savingHP = false;

  // Condition input state (per-combatant)
  let conditionInputs = {};

  // Round effects toast state
  let roundEffectsToast = [];
  let roundEffectsTimer = null;

  // --- Monster state ---
  let monsterInstances = [];  // { instanceId, monsterId, name, monster, hp_current, hp_max }
  let showAddMonster = false;
  let monsterSearch = '';
  let availableMonsters = [];
  let monsterQty = 1;
  let loadingMonsters = false;

  // Monster tooltip
  let tooltipMonster = null;
  let tooltipPos = { x: 0, y: 0 };
  let tooltipTimer = null;

  let nextMonsterId = 1;

  // Dice rolling
  let rollDice = null;

  // Parse dice notation from a damage string like "2d6", "1d8+1", "2d6+3 + poison"
  // Returns { dice, mod, extra } — dice is the rollable part, mod is the numeric bonus,
  // extra is any trailing text (effects, etc.)
  function parseDamage(damage) {
    if (!damage) return null;
    const match = damage.match(/^(\d+d\d+)([+-]\d+)?(.*)/i);
    if (!match) return null;
    const dice = match[1].trim();
    const mod = match[2] ? parseInt(match[2]) : 0;
    const extra = match[3].trim();
    return { dice, mod, extra };
  }

  async function rollMonsterAttack(thac0, monsterName) {
    if (!rollDice || thac0 == null) return;
    await rollDice('1d20', (roll) => {
      const acHit = thac0 - roll;
      return `${monsterName} \u2192 Hits AC ${acHit}`;
    });
  }

  async function rollMorale(morale, name) {
    if (!rollDice || morale == null) return;
    await rollDice('2d6', (roll) => {
      const result = roll <= morale ? 'Holds!' : 'Flees!';
      return `${name} ML ${morale} \u2192 ${result}`;
    });
  }

  async function rollMonsterDamage(atk, monsterName) {
    if (!rollDice) return;
    const parsed = parseDamage(atk.damage);
    if (!parsed) return;
    await rollDice(parsed.dice, (total) => {
      const dmg = total + parsed.mod;
      let text = `${monsterName} ${atk.name} \u2192 ${dmg} damage`;
      if (parsed.extra) text += ` ${parsed.extra}`;
      if (atk.effects) text += ` + ${atk.effects}`;
      return { display: dmg, text };
    });
  }

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

  // Build unified combatants list
  $: charCombatants = characters.map(c => ({
    id: String(c.id),
    type: 'character',
    subtype: c.character_type || 'pc',
    name: c.name,
    data: c,
  }));

  $: monsterCombatants = monsterInstances.map(m => ({
    id: m.instanceId,
    type: 'monster',
    name: m.name,
    data: m,
  }));

  $: allCombatants = [...charCombatants, ...monsterCombatants];

  $: sortedCombatants = encounterActive || Object.keys(initiatives).length > 0
    ? [...allCombatants].sort((a, b) => {
        const ai = initiatives[a.id] ?? 999;
        const bi = initiatives[b.id] ?? 999;
        return bi - ai || a.name.localeCompare(b.name);
      })
    : [...allCombatants].sort((a, b) => {
        // Characters first, then monsters
        if (a.type !== b.type) return a.type === 'character' ? -1 : 1;
        return a.name.localeCompare(b.name);
      });

  $: activeCombatantId = encounterActive && sortedCombatants.length > 0
    ? sortedCombatants[activeCombatantIndex % sortedCombatants.length]?.id
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
        activeCombatantIndex = enc.currentIndex || 0;
        if (enc.monsters) {
          // Restore monster instances — we'll re-hydrate data from API later
          monsterInstances = enc.monsters;
          nextMonsterId = Math.max(...monsterInstances.map(m => {
            const num = parseInt(m.instanceId.replace('m_', ''));
            return isNaN(num) ? 0 : num;
          }), 0) + 1;
        }
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
      currentIndex: activeCombatantIndex,
      monsters: monsterInstances.map(m => ({
        instanceId: m.instanceId,
        monsterId: m.monsterId,
        name: m.name,
        hp_current: m.hp_current,
        hp_max: m.hp_max,
        conditions: conditions[m.instanceId] || [],
      })),
    }));
  }

  function cleanupLocalState() {
    const charIds = new Set(characters.map(c => String(c.id)));
    const monsterIds = new Set(monsterInstances.map(m => m.instanceId));
    const allIds = new Set([...charIds, ...monsterIds]);
    let changed = false;
    for (const key of Object.keys(initiatives)) {
      if (!allIds.has(key)) { delete initiatives[key]; changed = true; }
    }
    for (const key of Object.keys(conditions)) {
      if (!allIds.has(key)) { delete conditions[key]; changed = true; }
    }
    if (changed) {
      saveInitiatives();
      saveConditions();
    }
    if (encounterActive && activeCombatantIndex >= sortedCombatants.length && sortedCombatants.length > 0) {
      activeCombatantIndex = 0;
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

  async function rehydrateMonsters() {
    // Re-fetch monster data for saved instances
    if (monsterInstances.length === 0) return;
    const uniqueIds = [...new Set(monsterInstances.map(m => m.monsterId))];
    for (const mid of uniqueIds) {
      try {
        const monsterData = await api.get(`/monsters/${mid}`);
        for (const inst of monsterInstances) {
          if (inst.monsterId === mid) {
            inst.monster = monsterData;
          }
        }
      } catch {
        // Monster may have been deleted — remove orphaned instances
        monsterInstances = monsterInstances.filter(m => m.monsterId !== mid);
      }
    }
    monsterInstances = monsterInstances;
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
    await rehydrateMonsters();
    loading = false;
    pollTimer = setInterval(fetchRefereeData, 5000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
    if (tooltipTimer) clearTimeout(tooltipTimer);
  });

  // --- HP ---

  function hpPct(current, max) {
    return max > 0 ? Math.round((current / max) * 100) : 0;
  }

  function hpColorClass(current, max) {
    const pct = hpPct(current, max);
    if (pct <= 25) return 'text-red-800 font-bold';
    if (pct <= 50) return 'text-amber-700';
    return 'text-green-800';
  }

  function startHPEdit(combatantId) {
    hpEditId = combatantId;
    hpDelta = '';
  }

  function handleHPKeydown(e, combatant) {
    if (e.key === 'Enter') submitHP(combatant);
    if (e.key === 'Escape') { hpEditId = null; hpDelta = ''; }
  }

  async function submitHP(combatant) {
    const val = parseInt(hpDelta);
    if (isNaN(val) || val === 0) {
      hpEditId = null;
      hpDelta = '';
      return;
    }

    if (combatant.type === 'character') {
      const char = combatant.data;
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
    } else {
      // Monster — local only
      const inst = combatant.data;
      inst.hp_current = Math.max(0, Math.min(inst.hp_max, inst.hp_current + val));
      monsterInstances = monsterInstances;
      hpEditId = null;
      hpDelta = '';
      saveEncounter();
    }
  }

  // --- Weapons ---

  function weaponDamageNotation(w) {
    let dmg = w.damage_dice;
    if (w.damage_mod > 0) dmg += `+${w.damage_mod}`;
    else if (w.damage_mod < 0) dmg += `${w.damage_mod}`;
    return dmg;
  }

  async function rollCharWeaponDamage(w, charName) {
    if (!rollDice || !w.damage_dice) return;
    await rollDice(w.damage_dice, (total) => {
      const dmg = total + (w.damage_mod || 0);
      return { display: dmg, text: `${charName} ${w.name} \u2192 ${dmg} damage` };
    });
  }

  // --- Initiative ---

  function handleInitChange(combatantId, value) {
    const num = parseInt(value);
    if (isNaN(num)) {
      delete initiatives[combatantId];
    } else {
      initiatives[combatantId] = num;
    }
    initiatives = initiatives;
    saveInitiatives();
  }

  // --- Conditions ---

  function addCondition(combatantId, input) {
    const raw = (input || '').trim();
    if (!raw) return;

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

    const list = conditions[combatantId] || [];
    list.push({ name, turns });
    conditions[combatantId] = list;
    conditions = conditions;
    saveConditions();

    conditionInputs[combatantId] = '';
    conditionInputs = conditionInputs;
  }

  function removeCondition(combatantId, index) {
    const list = conditions[combatantId] || [];
    list.splice(index, 1);
    conditions[combatantId] = list;
    conditions = conditions;
    saveConditions();
  }

  function handleConditionKeydown(e, combatantId) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addCondition(combatantId, conditionInputs[combatantId]);
    }
  }

  // --- Monster Management ---

  async function openAddMonster() {
    showAddMonster = true;
    monsterSearch = '';
    monsterQty = 1;
    if (availableMonsters.length === 0) {
      loadingMonsters = true;
      try {
        availableMonsters = await api.get(`/monsters/?campaign_id=${campaignId}&limit=500`);
      } catch {
        availableMonsters = [];
      } finally {
        loadingMonsters = false;
      }
    }
  }

  $: filteredMonsters = monsterSearch.trim()
    ? availableMonsters.filter(m => m.name.toLowerCase().includes(monsterSearch.toLowerCase()))
    : availableMonsters;

  function addMonsterToEncounter(monster) {
    const qty = Math.max(1, Math.min(20, monsterQty));
    for (let i = 0; i < qty; i++) {
      const instanceId = `m_${nextMonsterId++}`;
      const suffix = qty > 1 ? ` #${i + 1}` : (monsterInstances.some(m => m.monsterId === monster.id) ? ` #${monsterInstances.filter(m => m.monsterId === monster.id).length + i + 1}` : '');
      monsterInstances = [...monsterInstances, {
        instanceId,
        monsterId: monster.id,
        name: monster.name + suffix,
        monster,
        hp_current: monster.hp ?? 1,
        hp_max: monster.hp ?? 1,
      }];
    }
    saveEncounter();
    showAddMonster = false;
  }

  function removeMonster(instanceId) {
    monsterInstances = monsterInstances.filter(m => m.instanceId !== instanceId);
    delete initiatives[instanceId];
    delete conditions[instanceId];
    initiatives = initiatives;
    conditions = conditions;
    saveInitiatives();
    saveConditions();
    saveEncounter();
  }

  // --- Monster Tooltip ---

  function showTooltip(e, monster) {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    tooltipTimer = setTimeout(() => {
      tooltipMonster = monster;
      tooltipPos = { x: e.clientX, y: e.clientY };
    }, 300);
  }

  function hideTooltip() {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    tooltipTimer = null;
    tooltipMonster = null;
  }

  // --- Encounter Tracker ---

  function startEncounter() {
    encounterActive = true;
    encounterRound = 1;
    activeCombatantIndex = 0;
    saveEncounter();
  }

  function endEncounter() {
    encounterActive = false;
    encounterRound = 1;
    activeCombatantIndex = 0;
    // Clear monster instances on end
    monsterInstances = [];
    // Clean up monster initiatives/conditions
    for (const key of Object.keys(initiatives)) {
      if (key.startsWith('m_')) delete initiatives[key];
    }
    for (const key of Object.keys(conditions)) {
      if (key.startsWith('m_')) delete conditions[key];
    }
    initiatives = initiatives;
    conditions = conditions;
    saveInitiatives();
    saveConditions();
    saveEncounter();
  }

  function nextTurn() {
    if (!encounterActive || sortedCombatants.length === 0) return;

    const nextIndex = activeCombatantIndex + 1;

    if (nextIndex >= sortedCombatants.length) {
      activeCombatantIndex = 0;
      encounterRound += 1;
      tickDownConditions();
      applyRoundEffects();
    } else {
      activeCombatantIndex = nextIndex;
    }
    saveEncounter();
  }

  function prevTurn() {
    if (!encounterActive || sortedCombatants.length === 0) return;

    if (activeCombatantIndex > 0) {
      activeCombatantIndex -= 1;
    } else if (encounterRound > 1) {
      activeCombatantIndex = sortedCombatants.length - 1;
      encounterRound -= 1;
    }
    saveEncounter();
  }

  function tickDownConditions() {
    let changed = false;
    for (const combatantId of Object.keys(conditions)) {
      const list = conditions[combatantId];
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
      conditions[combatantId] = list;
    }
    if (changed) {
      conditions = conditions;
      saveConditions();
    }
  }

  async function applyRoundEffects() {
    try {
      const log = await api.post(`/campaigns/${campaignId}/round-effects`);
      if (!log || log.length === 0) return;

      for (const entry of log) {
        const char = characters.find(c => c.id === entry.character_id);
        if (char && entry.effects.length > 0) {
          const lastEffect = entry.effects[entry.effects.length - 1];
          char.hp_current = lastEffect.new_hp;
        }
      }
      characters = characters;

      const msgs = [];
      for (const entry of log) {
        for (const eff of entry.effects) {
          const sign = eff.value > 0 ? '+' : '';
          msgs.push(`${entry.character_name} ${sign}${eff.value} HP (${eff.item_name})`);
        }
      }
      roundEffectsToast = msgs;
      if (roundEffectsTimer) clearTimeout(roundEffectsTimer);
      roundEffectsTimer = setTimeout(() => { roundEffectsToast = []; roundEffectsTimer = null; }, 5000);
    } catch {
      // silently fail — poll will correct
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
  <DiceOverlay bind:roll={rollDice} />
  <PageWrapper title="Referee Panel" maxWidth="max-w-7xl">
    <!-- Header bar -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <a href="/campaigns/{campaignId}" class="text-xs text-ink-faint hover:text-ink">&larr; {campaign.name}</a>
        <span class="text-ink-faint text-xs">|</span>
        <a href="/campaigns/{campaignId}/referee/dungeon" class="text-xs text-ink-faint hover:text-ink">Dungeon Tracker</a>
      </div>

      <div class="flex items-center gap-3">
        <button class="btn-ghost text-xs" on:click={openAddMonster}>+ Add Monster</button>
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

    {#if allCombatants.length === 0}
      <div class="panel text-center py-6">
        <p class="text-ink-faint text-sm">No living characters in this campaign. Use "+ Add Monster" to add monsters.</p>
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
              <th class="text-left pb-2 px-2">Attacks</th>
              <th class="text-center pb-2 px-2">Move</th>
              <th class="text-center pb-2 px-2">ML</th>
              <th class="text-left pb-2 px-2 min-w-[180px]">Conditions</th>
              <th class="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {#each sortedCombatants as combatant, idx (combatant.id)}
              {@const isActive = encounterActive && combatant.id === activeCombatantId}
              {@const isMonster = combatant.type === 'monster'}
              <tr
                class="border-t border-parchment-200 transition-colors {isActive ? 'active-turn' : 'row-hover'} {isMonster ? 'monster-row' : ''}"
              >
                <!-- Initiative -->
                <td class="text-center py-1.5 px-2">
                  <input
                    class="input w-14 text-center text-sm py-0.5"
                    type="number"
                    value={initiatives[combatant.id] ?? ''}
                    on:input={(e) => handleInitChange(combatant.id, e.target.value)}
                    placeholder="--"
                  />
                </td>

                <!-- Name -->
                <td class="py-1.5 px-2">
                  {#if isMonster}
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <span
                      class="text-ink font-medium cursor-help monster-name"
                      on:mouseenter={(e) => showTooltip(e, combatant.data.monster)}
                      on:mouseleave={hideTooltip}
                    >
                      <span class="monster-badge">M</span>
                      {combatant.name}
                    </span>
                  {:else}
                    <a href="/characters/{combatant.data.id}" class="text-ink hover:underline font-medium">
                      {#if combatant.subtype === 'retainer'}<span class="retainer-badge">R</span>{/if}
                      {combatant.name}
                    </a>
                  {/if}
                  {#if isActive}
                    <span class="text-[10px] ml-1 text-amber-700 font-medium">&bull; active</span>
                  {/if}
                </td>

                <!-- Class -->
                <td class="py-1.5 px-2 text-ink-faint">
                  {#if isMonster}
                    Monster
                  {:else}
                    {combatant.data.character_class?.name ?? combatant.data.combat_stats?.monster_name ?? '?'} {combatant.data.level}
                  {/if}
                </td>

                <!-- AC -->
                <td class="text-center py-1.5 px-2 font-serif text-lg">
                  {#if isMonster}
                    {combatant.data.monster?.ac ?? '?'}
                  {:else}
                    {combatant.data.ac ?? '?'}
                  {/if}
                </td>

                <!-- HP -->
                <td class="text-center py-1.5 px-2">
                  {#if isMonster}
                    {@const m = combatant.data}
                    {@const pct = hpPct(m.hp_current, m.hp_max)}
                    {#if hpEditId === combatant.id}
                      <div class="flex items-center justify-center gap-1">
                        <input
                          class="input w-14 text-center text-sm py-0.5"
                          type="number"
                          placeholder="+/-"
                          bind:value={hpDelta}
                          on:keydown={(e) => handleHPKeydown(e, combatant)}
                          autofocus
                        />
                        <button class="btn text-xs px-1.5 py-0.5" on:click={() => submitHP(combatant)}>OK</button>
                      </div>
                    {:else}
                      <!-- svelte-ignore a11y-click-events-have-key-events -->
                      <!-- svelte-ignore a11y-no-static-element-interactions -->
                      <span
                        class="cursor-pointer hover:bg-parchment-100 rounded px-1 font-serif text-lg {hpColorClass(m.hp_current, m.hp_max)}"
                        on:click={() => startHPEdit(combatant.id)}
                        title="Click to adjust HP"
                      >
                        {m.hp_current}/{m.hp_max}
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
                  {:else}
                    {@const char = combatant.data}
                    {@const pct = hpPct(char.hp_current, char.hp_max)}
                    {#if hpEditId === combatant.id}
                      <div class="flex items-center justify-center gap-1">
                        <input
                          class="input w-14 text-center text-sm py-0.5"
                          type="number"
                          placeholder="+/-"
                          bind:value={hpDelta}
                          on:keydown={(e) => handleHPKeydown(e, combatant)}
                          autofocus
                        />
                        <button class="btn text-xs px-1.5 py-0.5" on:click={() => submitHP(combatant)} disabled={savingHP}>OK</button>
                      </div>
                    {:else}
                      <!-- svelte-ignore a11y-click-events-have-key-events -->
                      <!-- svelte-ignore a11y-no-static-element-interactions -->
                      <span
                        class="cursor-pointer hover:bg-parchment-100 rounded px-1 font-serif text-lg {hpColorClass(char.hp_current, char.hp_max)}"
                        on:click={() => startHPEdit(combatant.id)}
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
                  {/if}
                </td>

                <!-- THAC0 -->
                <td class="text-center py-1.5 px-2 font-serif text-lg">
                  {#if isMonster}
                    {#if combatant.data.monster?.thac0 != null}
                      <button
                        class="rollable"
                        disabled={!rollDice}
                        on:click={() => rollMonsterAttack(combatant.data.monster.thac0, combatant.name)}
                        title="Roll attack (1d20)"
                      >{combatant.data.monster.thac0}</button>
                    {:else}
                      ?
                    {/if}
                  {:else}
                    {combatant.data.thac0 ?? '?'}
                  {/if}
                </td>

                <!-- Attacks / Weapons -->
                <td class="py-1.5 px-2">
                  {#if isMonster}
                    {@const attacks = combatant.data.monster?.monster_metadata?.attacks || []}
                    {#if attacks.length}
                      {#each attacks as atk}
                        <div class="text-xs text-ink leading-snug">
                          {atk.name}:
                          {#if parseDamage(atk.damage)}
                            <button
                              class="rollable-inline"
                              disabled={!rollDice}
                              on:click={() => rollMonsterDamage(atk, combatant.name)}
                              title="Roll {atk.damage}"
                            >{atk.damage}</button>
                          {:else}
                            {atk.damage}
                          {/if}
                          {#if atk.effects}<span class="text-ink-faint">({atk.effects})</span>{/if}
                        </div>
                      {/each}
                    {:else}
                      <span class="text-xs text-ink-faint">None</span>
                    {/if}
                  {:else}
                    {#if combatant.data.equipped_weapons?.length}
                      {#each combatant.data.equipped_weapons as w}
                        <div class="text-xs text-ink leading-snug">
                          {w.name}:
                          {#if parseDamage(weaponDamageNotation(w))}
                            <button
                              class="rollable-inline"
                              disabled={!rollDice}
                              on:click={() => rollCharWeaponDamage(w, combatant.name)}
                              title="Roll {weaponDamageNotation(w)}"
                            >{weaponDamageNotation(w)}</button>
                          {:else}
                            {weaponDamageNotation(w)}
                          {/if}
                          {#if w.weapon_type === 'ranged' && w.ammo_name}
                            <span class="text-ink-faint">({w.ammo_name}: {w.ammo_count ?? '?'})</span>
                          {/if}
                        </div>
                      {/each}
                    {:else}
                      <span class="text-xs text-ink-faint">None</span>
                    {/if}
                  {/if}
                </td>

                <!-- Movement -->
                <td class="text-center py-1.5 px-2">
                  {#if isMonster}
                    {combatant.data.monster?.movement_rate ?? '?'}
                  {:else}
                    {@const mv = combatant.data.combat_stats?.effective_movement ?? combatant.data.movement_rate}
                    {mv != null ? `${mv}' (${Math.floor(mv / 3)}')` : '?'}
                  {/if}
                </td>

                <!-- Morale -->
                <td class="text-center py-1.5 px-2">
                  {#if isMonster && combatant.data.monster?.morale != null}
                    <button
                      class="rollable"
                      disabled={!rollDice}
                      on:click={() => rollMorale(combatant.data.monster.morale, combatant.name)}
                      title="Roll morale (2d6 vs {combatant.data.monster.morale})"
                    >{combatant.data.monster.morale}</button>
                  {:else if !isMonster && combatant.data.loyalty != null}
                    <button
                      class="rollable"
                      disabled={!rollDice}
                      on:click={() => rollMorale(combatant.data.loyalty, combatant.name)}
                      title="Roll loyalty (2d6 vs {combatant.data.loyalty})"
                    >{combatant.data.loyalty}</button>
                  {:else}
                    <span class="text-ink-faint">&mdash;</span>
                  {/if}
                </td>

                <!-- Conditions -->
                <td class="py-1.5 px-2">
                  {#if conditions[combatant.id]?.length}
                    <div class="flex flex-wrap gap-1 mb-1">
                      {#each conditions[combatant.id] as cond, ci}
                        <span class="condition-chip" class:condition-expiring={cond.turns != null && cond.turns <= 1}>
                          {cond.name}{#if cond.turns != null} <span class="condition-turns">({cond.turns})</span>{/if}
                          <!-- svelte-ignore a11y-click-events-have-key-events -->
                          <!-- svelte-ignore a11y-no-static-element-interactions -->
                          <span
                            class="condition-x"
                            on:click={() => removeCondition(combatant.id, ci)}
                            title="Remove condition"
                          >&times;</span>
                        </span>
                      {/each}
                    </div>
                  {/if}
                  <input
                    class="input w-full text-xs py-0.5"
                    type="text"
                    bind:value={conditionInputs[combatant.id]}
                    on:keydown={(e) => handleConditionKeydown(e, combatant.id)}
                    placeholder="name or name-turns"
                  />
                </td>

                <!-- Remove (monsters only) -->
                <td class="text-center py-1.5 px-1">
                  {#if isMonster}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <span
                      class="cursor-pointer text-ink-faint hover:text-red-700 text-sm"
                      on:click={() => removeMonster(combatant.id)}
                      title="Remove monster"
                    >&times;</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </PageWrapper>
{/if}

<!-- Add Monster Modal -->
{#if showAddMonster}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center print:hidden" on:click|self={() => showAddMonster = false}>
    <div class="panel w-full max-w-lg max-h-[80vh] flex flex-col referee-modal">
      <div class="flex items-center justify-between mb-3">
        <h2 class="section-title">Add Monster</h2>
        <button class="btn-ghost text-xs" on:click={() => showAddMonster = false}>&times; Close</button>
      </div>
      <div class="flex gap-2 mb-3">
        <input
          class="input flex-1"
          type="text"
          bind:value={monsterSearch}
          placeholder="Search monsters..."
          autofocus
        />
        <div class="flex items-center gap-1">
          <label class="text-xs text-ink-faint" for="monster-qty">Qty</label>
          <input id="monster-qty" class="input w-14 text-center" type="number" min="1" max="20" bind:value={monsterQty} />
        </div>
      </div>
      <div class="overflow-y-auto flex-1 -mx-4 px-4">
        {#if loadingMonsters}
          <p class="text-ink-faint text-sm">Loading...</p>
        {:else if filteredMonsters.length === 0}
          <p class="text-ink-faint text-sm">No monsters found.</p>
        {:else}
          {#each filteredMonsters as monster}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
              class="py-2 px-2 rounded cursor-pointer hover:bg-parchment-200 transition-colors border-b border-parchment-100"
              on:click={() => addMonsterToEncounter(monster)}
            >
              <div class="font-medium text-ink">{monster.name}</div>
              <div class="text-xs text-ink-faint flex gap-3">
                {#if monster.ac != null}<span>AC {monster.ac}</span>{/if}
                {#if monster.hit_dice}<span>HD {monster.hit_dice}</span>{/if}
                {#if monster.hp != null}<span>HP {monster.hp}</span>{/if}
                {#if monster.thac0 != null}<span>THAC0 {monster.thac0}</span>{/if}
                {#if monster.xp != null}<span>XP {monster.xp}</span>{/if}
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Monster Tooltip -->
{#if tooltipMonster}
  {@const tm = tooltipMonster}
  {@const tmeta = tm.monster_metadata || {}}
  <div
    class="fixed z-50 shadow-lg rounded-sm p-4 border border-ink-faint bg-parchment-50 text-sm max-w-xs pointer-events-none print:hidden monster-tooltip"
    style="left: {Math.min(tooltipPos.x + 12, (typeof window !== 'undefined' ? window.innerWidth - 320 : 400))}px; top: {Math.max(tooltipPos.y - 10, 10)}px;"
  >
    <div class="font-serif text-lg text-ink mb-1">{tm.name}</div>
    <div class="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs mb-2">
      <div><span class="text-ink-faint">AC:</span> {tm.ac ?? '—'}</div>
      <div><span class="text-ink-faint">HD:</span> {tm.hit_dice ?? '—'}</div>
      <div><span class="text-ink-faint">HP:</span> {tm.hp ?? '—'}</div>
      <div><span class="text-ink-faint">THAC0:</span> {tm.thac0 ?? '—'}</div>
      <div><span class="text-ink-faint">Move:</span> {tm.movement_rate ?? '—'}</div>
      <div><span class="text-ink-faint">Morale:</span> {tm.morale ?? '—'}</div>
    </div>
    {#if tmeta.saves}
      <div class="text-xs mb-1">
        <span class="text-ink-faint">Saves:</span>
        D:{tmeta.saves.D ?? '—'} W:{tmeta.saves.W ?? '—'} P:{tmeta.saves.P ?? '—'} B:{tmeta.saves.B ?? '—'} S:{tmeta.saves.S ?? '—'}
      </div>
    {/if}
    {#if tmeta.attacks?.length}
      <div class="text-xs mb-1">
        <span class="text-ink-faint">Attacks:</span>
        {#each tmeta.attacks as atk}
          <div class="ml-2">{atk.name}: {atk.damage}{#if atk.effects} — {atk.effects}{/if}</div>
        {/each}
      </div>
    {/if}
    {#if tmeta.abilities && Object.keys(tmeta.abilities).length > 0}
      <div class="text-xs">
        <span class="text-ink-faint">Abilities:</span>
        {#each Object.entries(tmeta.abilities) as [aName, aDesc]}
          <div class="ml-2"><strong>{aName}:</strong> {aDesc}</div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<!-- Round Effects Toast -->
{#if roundEffectsToast.length > 0}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed bottom-6 right-6 z-50 shadow-lg rounded-sm p-4 border border-green-800/30 bg-green-50 min-w-[220px] max-w-[360px] cursor-pointer print:hidden"
    on:click={() => { roundEffectsToast = []; }}
  >
    <div class="text-xs text-green-800 font-bold uppercase tracking-wide mb-1">Round Effects</div>
    {#each roundEffectsToast as msg}
      <div class="text-sm text-green-900">{msg}</div>
    {/each}
  </div>
{/if}

<style>
  .active-turn {
    background-color: rgba(180, 140, 60, 0.15);
    box-shadow: inset 3px 0 0 0 rgb(180, 140, 60);
  }

  .monster-row {
    background-color: rgba(153, 27, 27, 0.04);
  }

  .monster-row:hover {
    background-color: rgba(153, 27, 27, 0.08);
  }

  .monster-badge, .retainer-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.1rem;
    height: 1.1rem;
    font-size: 0.6rem;
    font-weight: 700;
    line-height: 1;
    border-radius: 0.2rem;
    margin-right: 0.25rem;
    vertical-align: middle;
  }

  .monster-badge {
    background-color: rgba(153, 27, 27, 0.15);
    color: rgb(153, 27, 27);
  }

  .retainer-badge {
    background-color: rgba(37, 99, 235, 0.15);
    color: rgb(37, 99, 235);
  }

  .monster-name {
    border-bottom: 1px dotted rgba(107, 92, 74, 0.3);
  }

  .monster-tooltip {
    border-left: 3px solid rgb(153, 27, 27);
  }

  .condition-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.65rem;
    line-height: 1.4;
    padding: 0.05rem 0.4rem;
    border-radius: 0.25rem;
    background-color: rgb(var(--color-parchment-200));
    color: rgb(var(--color-ink-faint));
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

  .rollable {
    background: none;
    border: none;
    font: inherit;
    color: inherit;
    cursor: pointer;
    padding: 0 0.15rem;
    border-radius: 0.2rem;
    border-bottom: 2px dotted rgba(153, 27, 27, 0.4);
    transition: background-color 0.15s, color 0.15s;
  }

  .rollable:hover:not(:disabled) {
    background-color: rgba(153, 27, 27, 0.1);
    color: rgb(153, 27, 27);
  }

  .rollable:disabled {
    cursor: default;
    border-bottom-color: transparent;
  }

  .rollable-inline {
    background: none;
    border: none;
    font: inherit;
    font-size: inherit;
    color: inherit;
    cursor: pointer;
    padding: 0 0.1rem;
    border-bottom: 1px dotted rgba(153, 27, 27, 0.4);
    transition: background-color 0.15s, color 0.15s;
  }

  .rollable-inline:hover:not(:disabled) {
    background-color: rgba(153, 27, 27, 0.1);
    color: rgb(153, 27, 27);
  }

  .rollable-inline:disabled {
    cursor: default;
    border-bottom-color: transparent;
  }

  .referee-modal {
    background: rgb(var(--color-parchment-50, 250 245 235)) !important;
    border: 1px solid rgba(107, 92, 74, 0.2) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25) !important;
  }
</style>
