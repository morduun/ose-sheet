<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import DiceOverlay from '$lib/components/shared/DiceOverlay.svelte';

  const campaignId = $page.params.id;

  let campaign = null;
  let characters = [];
  let vehicles = [];
  let loading = true;
  let error = '';
  let userId = null;
  let rollDice = null;

  // --- Travel state (localStorage-backed) ---
  let currentDay = 0;
  let terrain = 'clear';
  let onRoad = false;
  let waterborne = false;
  let forcedMarch = false;
  let needsRest = false;
  let daysSinceRest = 0;
  let travelLog = [];
  let dayNotes = '';

  // Waterborne state
  let windResult = null;
  let selectedVehicleId = null;

  // --- Constants ---
  const TERRAINS = [
    { key: 'clear', label: 'Clear / Grasslands', speedMod: 1, lostChance: 1, encounterChance: 1 },
    { key: 'barren', label: 'Barren Lands', speedMod: 0.67, lostChance: 2, encounterChance: 2 },
    { key: 'desert', label: 'Desert', speedMod: 0.67, lostChance: 3, encounterChance: 2 },
    { key: 'forest', label: 'Forest / Woods', speedMod: 0.67, lostChance: 2, encounterChance: 2 },
    { key: 'hills', label: 'Hills', speedMod: 0.67, lostChance: 2, encounterChance: 2 },
    { key: 'jungle', label: 'Jungle', speedMod: 0.5, lostChance: 3, encounterChance: 3 },
    { key: 'mountains', label: 'Mountains', speedMod: 0.5, lostChance: 2, encounterChance: 3 },
    { key: 'swamp', label: 'Swamp', speedMod: 0.5, lostChance: 3, encounterChance: 3 },
    { key: 'settled', label: 'Settled Lands', speedMod: 1, lostChance: 1, encounterChance: 1 },
  ];

  const WIND_TABLE = [
    { roll: 2, wind: 'No Wind', effect: 'Sailing impossible. Oar at 1/3 rate.', sailMod: 0, oarMod: 0.33 },
    { roll: 3, wind: 'Faint Breeze', effect: 'Sailing at 1/3 normal.', sailMod: 0.33 },
    { roll: 4, wind: 'Gentle Breeze', effect: 'Sailing at 1/2 normal.', sailMod: 0.5 },
    { roll: 5, wind: 'Moderate Breeze', effect: 'Sailing at 2/3 normal.', sailMod: 0.67 },
    { roll: 8, wind: 'Fresh Breeze', effect: 'Normal sailing.', sailMod: 1 },
    { roll: 9, wind: 'Strong Breeze', effect: 'Sailing +1/3.', sailMod: 1.33 },
    { roll: 10, wind: 'High Wind', effect: 'Sailing +1/2.', sailMod: 1.5 },
    { roll: 11, wind: 'Near Gale', effect: 'Sailing doubled. Risk of taking on water.', sailMod: 2, hazard: 'near_gale' },
    { roll: 12, wind: 'Gale / Storm', effect: 'Sailing tripled. Extreme danger!', sailMod: 3, hazard: 'gale' },
  ];

  // --- Derived: party composition ---
  $: activeChars = characters.filter(c => c.is_alive && c.character_type === 'pc');
  $: partyClasses = activeChars.map(c => c.character_class?.name ?? '').filter(Boolean);
  // Include retainers for class bonuses
  $: allClasses = characters.filter(c => c.is_alive).map(c => c.character_class?.name ?? '').filter(Boolean);
  $: hasBarbarian = allClasses.some(n => n === 'Barbarian');
  $: hasRanger = allClasses.some(n => n === 'Ranger');
  $: hasDruid = allClasses.some(n => n === 'Druid');
  $: hasForagingBonus = hasBarbarian || hasRanger;

  // --- Derived: current terrain info ---
  $: currentTerrain = TERRAINS.find(t => t.key === terrain) || TERRAINS[0];

  // Lost chance with druid override
  $: effectiveLostChance = (() => {
    let chance = currentTerrain.lostChance;
    if (hasDruid && (terrain === 'forest')) chance = Math.min(chance, 1);
    return chance;
  })();

  // --- Derived: movement ---
  $: slowestMovement = (() => {
    if (activeChars.length === 0) return 120;
    return Math.min(...activeChars.map(c =>
      c.combat_stats?.effective_movement ?? c.movement_rate ?? 120
    ));
  })();

  $: baseMilesPerDay = Math.floor(slowestMovement / 5);
  $: terrainMiles = Math.floor(baseMilesPerDay * currentTerrain.speedMod);
  $: roadMiles = onRoad ? Math.floor(terrainMiles * 1.5) : terrainMiles;
  $: effectiveMiles = forcedMarch ? Math.floor(roadMiles * 1.5) : roadMiles;

  // Waterborne
  $: selectedVehicle = vehicles.find(v => v.id === selectedVehicleId) || null;
  $: shipMilesPerDay = selectedVehicle ? Math.floor(selectedVehicle.effective_movement / 5) : 0;
  $: effectiveWaterMiles = (() => {
    if (!selectedVehicle || !windResult) return shipMilesPerDay;
    return Math.floor(shipMilesPerDay * (windResult.sailMod ?? 1));
  })();

  // --- Auth ---
  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch { return null; }
  }

  $: isGM = campaign && userId && campaign.gm_id === userId;
  $: if (browser && campaign && !isGM) goto(`/campaigns/${campaignId}`);

  // --- Persistence ---
  const STORAGE_KEY = `overland_${campaignId}`;

  function saveState() {
    if (!browser) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      currentDay, terrain, onRoad, waterborne, forcedMarch, needsRest,
      daysSinceRest, travelLog, selectedVehicleId,
    }));
  }

  function loadState() {
    if (!browser) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      currentDay = s.currentDay || 0;
      terrain = s.terrain || 'clear';
      onRoad = s.onRoad || false;
      waterborne = s.waterborne || false;
      forcedMarch = s.forcedMarch || false;
      needsRest = s.needsRest || false;
      daysSinceRest = s.daysSinceRest || 0;
      travelLog = s.travelLog || [];
      selectedVehicleId = s.selectedVehicleId || null;
    } catch { /* defaults */ }
  }

  // --- Data loading ---
  onMount(async () => {
    userId = getUserId();
    loadState();
    try {
      campaign = await api.get(`/campaigns/${campaignId}`);
      const data = await api.get(`/campaigns/${campaignId}/referee`);
      characters = data;
      try {
        vehicles = await api.get(`/campaigns/${campaignId}/vehicles`);
      } catch { vehicles = []; }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  // --- Actions ---
  function rollD6() { return Math.floor(Math.random() * 6) + 1; }

  function startDay() {
    currentDay++;
    dayNotes = '';
    windResult = null;
    if (needsRest) {
      addLogEvent('Forced march fatigue — party needs rest today.');
    }
    saveState();
  }

  function addLogEvent(text) {
    const entry = travelLog.find(l => l.day === currentDay);
    if (entry) {
      entry.events.push(text);
    } else {
      travelLog.push({
        day: currentDay,
        terrain: currentTerrain.label,
        onRoad,
        waterborne,
        miles: waterborne ? effectiveWaterMiles : effectiveMiles,
        events: [text],
        notes: '',
      });
    }
    travelLog = travelLog;
    saveState();
  }

  async function rollDirection() {
    if (!rollDice) return;
    const chance = waterborne ? 2 : effectiveLostChance;
    const total = await rollDice('1d6', (roll) => {
      const lost = roll <= chance;
      let text = `Direction: ${roll} vs ${chance}-in-6`;
      if (hasDruid && terrain === 'forest' && !waterborne) text += ' (Druid bonus)';
      text += lost ? ' — LOST!' : ' — On course.';
      return { display: roll, text };
    });
    if (total != null) {
      const lost = total <= chance;
      addLogEvent(lost ? `Lost direction (rolled ${total} vs ${chance}-in-6)` : `On course (rolled ${total} vs ${chance}-in-6)`);
    }
  }

  async function rollWanderingMonster() {
    if (!rollDice) return;
    const chance = waterborne ? 2 : currentTerrain.encounterChance;
    const total = await rollDice('1d6', (roll) => {
      const encounter = roll <= chance;
      return { display: roll, text: encounter ? `Wandering Monster! (${roll} vs ${chance}-in-6)` : `No encounter (${roll} vs ${chance}-in-6)` };
    });
    if (total != null) {
      const encounter = total <= chance;
      if (encounter) {
        const dist = (rollD6() + rollD6() + rollD6() + rollD6()) * 10;
        addLogEvent(`Wandering monster encountered at ${dist} yards!`);
      } else {
        addLogEvent(`No wandering monster (rolled ${total} vs ${chance}-in-6)`);
      }
    }
  }

  async function rollForage() {
    if (!rollDice) return;
    const chance = hasForagingBonus ? 2 : 1;
    const total = await rollDice('1d6', (roll) => {
      const found = roll <= chance;
      let text = `Forage: ${roll} vs ${chance}-in-6`;
      if (hasForagingBonus) text += ' (Barbarian/Ranger bonus)';
      text += found ? ' — Food found!' : ' — Nothing.';
      return { display: roll, text };
    });
    if (total != null) {
      const found = total <= chance;
      if (found) {
        const rations = rollD6();
        addLogEvent(`Foraging: found food for ${rations} people (rolled ${total} vs ${chance}-in-6)`);
      } else {
        addLogEvent(`Foraging: nothing found (rolled ${total} vs ${chance}-in-6)`);
      }
    }
  }

  async function rollHunt() {
    if (!rollDice) return;
    const chance = hasForagingBonus ? 2 : 1;
    const total = await rollDice('1d6', (roll) => {
      const found = roll <= chance;
      let text = `Hunt: ${roll} vs ${chance}-in-6`;
      if (hasForagingBonus) text += ' (Barbarian/Ranger bonus)';
      text += found ? ' — Game found!' : ' — No game.';
      return { display: roll, text };
    });
    if (total != null) {
      const found = total <= chance;
      addLogEvent(found
        ? `Hunting: game encountered (rolled ${total} vs ${chance}-in-6) — no travel today`
        : `Hunting: no game (rolled ${total} vs ${chance}-in-6) — no travel today`
      );
    }
  }

  async function rollWind() {
    if (!rollDice) return;
    const total = await rollDice('2d6', (roll) => {
      const entry = WIND_TABLE.find(w => roll <= w.roll) || WIND_TABLE[WIND_TABLE.length - 1];
      return { display: roll, text: `Wind: ${entry.wind} — ${entry.effect}` };
    });
    if (total != null) {
      const entry = WIND_TABLE.find(w => total <= w.roll) || WIND_TABLE[WIND_TABLE.length - 1];
      windResult = entry;
      addLogEvent(`Wind conditions: ${entry.wind} (rolled ${total}) — ${entry.effect}`);
    }
  }

  function endDay() {
    // Update log entry with final data
    const entry = travelLog.find(l => l.day === currentDay);
    if (entry) {
      entry.miles = waterborne ? effectiveWaterMiles : effectiveMiles;
      entry.notes = dayNotes;
      entry.terrain = currentTerrain.label + (onRoad ? ' (road)' : '');
      entry.waterborne = waterborne;
    }

    daysSinceRest++;
    if (forcedMarch) {
      needsRest = true;
      forcedMarch = false;
    }

    travelLog = travelLog;
    saveState();
  }

  function restDay() {
    addLogEvent('Rest day — no travel. Party recovers from fatigue.');
    daysSinceRest = 0;
    needsRest = false;
    forcedMarch = false;
    saveState();
  }

  function resetTracker() {
    currentDay = 0;
    travelLog = [];
    daysSinceRest = 0;
    needsRest = false;
    forcedMarch = false;
    windResult = null;
    dayNotes = '';
    saveState();
  }
</script>

<svelte:head>
  <title>Overland Travel — {campaign?.name ?? 'Campaign'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading...</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if campaign}
  <DiceOverlay bind:roll={rollDice} />
  <PageWrapper title="Overland Travel" maxWidth="max-w-5xl">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <a href="/campaigns/{campaignId}/referee" class="text-xs text-ink-faint hover:text-ink">&larr; Referee Panel</a>
        <span class="text-ink-faint text-xs">|</span>
        <a href="/campaigns/{campaignId}/referee/dungeon" class="text-xs text-ink-faint hover:text-ink">Dungeon Tracker</a>
      </div>
      <div class="flex items-center gap-2">
        {#if currentDay > 0}
          <div class="panel py-1.5 px-3">
            <span class="text-xs text-ink-faint uppercase tracking-wide">Day</span>
            <span class="font-serif text-xl text-ink leading-none ml-1">{currentDay}</span>
          </div>
        {/if}
        <button class="btn-ghost text-xs" on:click={resetTracker}>Reset</button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Left column: Controls -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Terrain & Mode -->
        <div class="panel">
          <h2 class="section-title">Travel Settings</h2>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="sm:col-span-2">
              <label class="block text-xs text-ink-faint mb-1" for="terrain">Terrain</label>
              <select id="terrain" class="input w-full" bind:value={terrain} on:change={saveState}>
                {#each TERRAINS as t}
                  <option value={t.key}>{t.label}</option>
                {/each}
              </select>
            </div>
            <div class="flex flex-col gap-2 justify-end">
              <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
                <input type="checkbox" bind:checked={onRoad} on:change={saveState} class="accent-ink" />
                Maintained Road
              </label>
              <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
                <input type="checkbox" bind:checked={waterborne} on:change={saveState} class="accent-ink" />
                Waterborne
              </label>
            </div>
            <div class="flex flex-col gap-2 justify-end">
              <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
                <input type="checkbox" bind:checked={forcedMarch} on:change={saveState} class="accent-ink" />
                Forced March
              </label>
            </div>
          </div>

          {#if waterborne}
            <div class="mt-3 pt-3 border-t border-parchment-200">
              <label class="block text-xs text-ink-faint mb-1" for="vehicle">Vessel</label>
              <select id="vehicle" class="input w-full" bind:value={selectedVehicleId} on:change={saveState}>
                <option value={null}>None (swimming?)</option>
                {#each vehicles as v}
                  <option value={v.id}>{v.name} — {v.effective_movement}' ({Math.floor(v.effective_movement / 5)} mi/day)</option>
                {/each}
              </select>
            </div>
          {/if}
        </div>

        <!-- Speed Summary -->
        <div class="panel">
          <h2 class="section-title">Today's Travel</h2>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <div class="text-center border border-ink-faint/30 rounded-sm p-2">
              <div class="text-xs text-ink-faint uppercase">Slowest PC</div>
              <div class="font-serif text-2xl text-ink">{slowestMovement}'</div>
            </div>
            <div class="text-center border border-ink-faint/30 rounded-sm p-2">
              <div class="text-xs text-ink-faint uppercase">Base Mi/Day</div>
              <div class="font-serif text-2xl text-ink">{baseMilesPerDay}</div>
            </div>
            <div class="text-center border border-ink-faint/30 rounded-sm p-2">
              <div class="text-xs text-ink-faint uppercase">{waterborne ? 'Ship Mi/Day' : 'Terrain Adj.'}</div>
              <div class="font-serif text-2xl text-ink">{waterborne ? effectiveWaterMiles : roadMiles}</div>
            </div>
            <div class="text-center border border-ink-faint/30 rounded-sm p-2 {forcedMarch ? 'bg-amber-50 border-amber-400' : ''} {needsRest ? 'bg-red-50 border-red-400' : ''}">
              <div class="text-xs text-ink-faint uppercase">Effective</div>
              <div class="font-serif text-2xl text-ink">{waterborne ? effectiveWaterMiles : effectiveMiles} mi</div>
              {#if forcedMarch}<div class="text-[10px] text-amber-700">Forced March</div>{/if}
              {#if needsRest}<div class="text-[10px] text-red-700">Must Rest!</div>{/if}
            </div>
          </div>

          <!-- Terrain info -->
          <div class="flex flex-wrap gap-4 text-xs text-ink-faint">
            <span>Lost: {effectiveLostChance}-in-6{hasDruid && terrain === 'forest' ? ' (Druid)' : ''}</span>
            <span>Encounter: {waterborne ? 2 : currentTerrain.encounterChance}-in-6</span>
            <span>Forage: {hasForagingBonus ? 2 : 1}-in-6{hasForagingBonus ? ' (Barbarian/Ranger)' : ''}</span>
            <span>Days since rest: {daysSinceRest}{daysSinceRest >= 6 ? ' (-1 to hit/dmg!)' : ''}</span>
          </div>
        </div>

        <!-- Day Actions -->
        <div class="panel">
          <h2 class="section-title">Actions</h2>
          {#if currentDay === 0}
            <button class="btn" on:click={startDay}>Start Journey (Day 1)</button>
          {:else}
            <div class="flex flex-wrap gap-2 mb-3">
              <button class="btn text-xs" on:click={rollDirection} disabled={!rollDice}>Roll Direction</button>
              {#if waterborne}
                <button class="btn text-xs" on:click={rollWind} disabled={!rollDice}>Roll Wind</button>
              {/if}
              <button class="btn text-xs" on:click={rollWanderingMonster} disabled={!rollDice}>Roll Wandering Monster</button>
              <button class="btn-ghost text-xs" on:click={rollForage} disabled={!rollDice}>Forage</button>
              <button class="btn-ghost text-xs" on:click={rollHunt} disabled={!rollDice}>Hunt (full day)</button>
              <button class="btn-ghost text-xs" on:click={restDay}>Rest Day</button>
            </div>

            {#if windResult}
              <div class="text-sm text-ink mb-3 p-2 rounded border border-ink-faint/30 {windResult.hazard === 'gale' ? 'bg-red-50 border-red-400' : windResult.hazard === 'near_gale' ? 'bg-amber-50 border-amber-400' : 'bg-parchment-100'}">
                Wind: <strong>{windResult.wind}</strong> — {windResult.effect}
              </div>
            {/if}

            <div class="mb-3">
              <label class="block text-xs text-ink-faint mb-1" for="day-notes">Day Notes</label>
              <textarea id="day-notes" class="input w-full resize-none text-sm" rows="2" bind:value={dayNotes} placeholder="What happened today..."></textarea>
            </div>

            <div class="flex gap-2">
              <button class="btn" on:click={() => { endDay(); startDay(); }}>End Day &rarr; Next</button>
              <button class="btn-ghost" on:click={endDay}>End Day (pause)</button>
            </div>
          {/if}
        </div>
      </div>

      <!-- Right column: Vehicles & Log -->
      <div class="space-y-4">
        <!-- Party Vehicles -->
        {#if vehicles.length > 0}
          <div class="panel">
            <h2 class="section-title">Party Vehicles</h2>
            <div class="space-y-2">
              {#each vehicles as v}
                {@const hpPct = v.hp_max > 0 ? Math.round((v.hp_current / v.hp_max) * 100) : 0}
                {@const isSelected = waterborne && selectedVehicleId === v.id}
                <div class="p-2 rounded border text-sm {isSelected ? 'border-ink bg-parchment-100' : 'border-ink-faint/30'}">
                  <div class="flex items-center justify-between">
                    <span class="font-medium text-ink">{v.name}</span>
                    <span class="text-xs text-ink-faint">{v.effective_movement}' ({Math.floor(v.effective_movement / 5)} mi/d)</span>
                  </div>
                  <div class="flex items-center gap-3 text-xs text-ink-faint mt-0.5">
                    <span>HP {v.hp_current}/{v.hp_max}</span>
                    <span>AC {v.ac}</span>
                    <span>Cargo {v.cargo_weight.toLocaleString()}/{v.cargo_capacity.toLocaleString()}</span>
                  </div>
                  <div class="h-1 bg-parchment-200 rounded mt-1">
                    <div
                      class="h-full rounded transition-all {hpPct <= 25 ? 'bg-red-700' : hpPct <= 50 ? 'bg-orange-600' : 'bg-green-600'}"
                      style="width: {hpPct}%"
                    ></div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Class Bonuses -->
        {#if hasBarbarian || hasRanger || hasDruid}
          <div class="panel">
            <h2 class="section-title">Party Bonuses</h2>
            <div class="space-y-1 text-xs text-ink-faint">
              {#if hasBarbarian}<div>Barbarian: improved foraging & hunting</div>{/if}
              {#if hasRanger}<div>Ranger: improved foraging & hunting</div>{/if}
              {#if hasDruid}<div>Druid: reduced lost chance in forests (1-in-6)</div>{/if}
            </div>
          </div>
        {/if}

        <!-- Travel Log -->
        <div class="panel">
          <h2 class="section-title">Travel Log</h2>
          {#if travelLog.length === 0}
            <p class="text-ink-faint text-xs">No travel recorded yet.</p>
          {:else}
            <div class="space-y-2 max-h-96 overflow-y-auto">
              {#each [...travelLog].reverse() as entry}
                <div class="text-xs border-b border-parchment-200 pb-2 last:border-0">
                  <div class="flex justify-between">
                    <span class="font-medium text-ink">Day {entry.day}</span>
                    <span class="text-ink-faint">{entry.miles} mi — {entry.terrain}</span>
                  </div>
                  {#each entry.events as event}
                    <div class="text-ink-faint ml-2">{event}</div>
                  {/each}
                  {#if entry.notes}
                    <div class="text-ink-light ml-2 italic">{entry.notes}</div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </PageWrapper>
{/if}
