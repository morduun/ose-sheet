<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Modal from '$lib/components/shared/Modal.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import DiceOverlay from '$lib/components/shared/DiceOverlay.svelte';
  import Markdown from '$lib/components/shared/Markdown.svelte';
  import DungeonTimeWidget from '$lib/components/dungeon/DungeonTimeWidget.svelte';

  const campaignId = $page.params.id;
  const dungeonId = $page.params.dungeonId;

  let dungeon = null;
  let loading = true;
  let error = '';
  let userId = null;
  let campaign = null;
  let rollDice = null;

  // Selected room
  let selectedRoomId = null;
  let currentSection = null;  // active section for wandering monster rolls

  // Dungeon edit modal
  let showDungeonEditor = false;
  let dungeonEditName = '';
  let dungeonEditDesc = '';
  let dungeonEditSections = [];

  // Room editor modal
  let showRoomEditor = false;
  let editingRoom = null;
  let roomForm = resetRoomForm();

  // Monster/item lookups
  let monsters = [];
  let items = [];

  const STATE_COLORS = {
    unvisited: 'bg-parchment-200 text-ink-faint',
    visited: 'bg-amber-100 text-amber-800',
    cleared: 'bg-green-100 text-green-800',
  };
  const STATE_LABELS = { unvisited: 'Unvisited', visited: 'Visited', cleared: 'Cleared' };
  const STATES = ['unvisited', 'visited', 'cleared'];

  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch { return null; }
  }

  $: isGM = campaign && userId && campaign.gm_id === userId;
  $: rooms = dungeon?.rooms ?? [];
  $: sections = dungeon?.sections ?? [];
  $: sectionNames = sections.map(s => s.name);
  $: selectedRoom = rooms.find(r => r.id === selectedRoomId) || null;

  // Auto-set currentSection when selecting a room
  $: if (selectedRoom?.section && selectedRoom.section !== currentSection) {
    currentSection = selectedRoom.section;
  }

  // Group rooms by section
  $: roomsBySection = (() => {
    const groups = [];
    const sectionOrder = [...sectionNames, null]; // null = unsectioned
    for (const sName of sectionOrder) {
      const sectionRooms = rooms.filter(r => (r.section || null) === sName);
      if (sectionRooms.length > 0 || sName !== null) {
        groups.push({ name: sName, label: sName || 'Unsectioned', rooms: sectionRooms });
      }
    }
    // Add any rooms with sections not in the section list
    const knownSections = new Set([...sectionNames, null]);
    const orphanSections = [...new Set(rooms.map(r => r.section).filter(s => s && !knownSections.has(s)))];
    for (const s of orphanSections) {
      groups.push({ name: s, label: s, rooms: rooms.filter(r => r.section === s) });
    }
    return groups.filter(g => g.rooms.length > 0);
  })();

  $: currentSectionData = sections.find(s => s.name === currentSection) || null;

  onMount(async () => {
    userId = getUserId();
    try {
      campaign = await api.get(`/campaigns/${campaignId}`);
      dungeon = await api.get(`/campaigns/${campaignId}/dungeons/${dungeonId}`);
      if (dungeon.rooms.length > 0) selectedRoomId = dungeon.rooms[0].id;
      // Preload monsters and items for the editor
      try { monsters = await api.get(`/monsters/?campaign_id=${campaignId}&limit=500`); } catch { monsters = []; }
      try { items = await api.get(`/items/?campaign_id=${campaignId}&limit=500`); } catch { items = []; }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function reload() {
    dungeon = await api.get(`/campaigns/${campaignId}/dungeons/${dungeonId}`);
  }

  // --- Room CRUD ---

  function resetRoomForm() {
    return {
      room_number: (rooms?.length ?? 0) + 1,
      name: '',
      description: '',
      notes: '',
      treasure_type_key: '',
      section: currentSection || '',
      monsters: [],
      items: [],
      traps: [],
      exits: [],
      currency: [],
    };
  }

  function openAddRoom() {
    editingRoom = null;
    roomForm = { ...resetRoomForm(), room_number: rooms.length + 1 };
    showRoomEditor = true;
  }

  function openEditRoom(room) {
    editingRoom = room;
    roomForm = {
      room_number: room.room_number,
      name: room.name,
      description: room.description || '',
      notes: room.notes || '',
      treasure_type_key: room.treasure_type_key || '',
      monsters: [...(room.monsters || [])],
      items: [...(room.items || [])],
      section: room.section || '',
      traps: [...(room.traps || [])],
      exits: [...(room.exits || [])],
      currency: (room.currency || []).map(c => ({ ...c })),
    };
    showRoomEditor = true;
  }

  async function saveRoom() {
    const payload = {
      ...roomForm,
      treasure_type_key: roomForm.treasure_type_key || null,
      description: roomForm.description || null,
      notes: roomForm.notes || null,
    };

    try {
      if (editingRoom) {
        await api.patch(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${editingRoom.id}`, payload);
      } else {
        const created = await api.post(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms`, payload);
        selectedRoomId = created.id;
      }
      await reload();
      showRoomEditor = false;
    } catch (e) {
      alert(e.message);
    }
  }

  async function deleteRoom(room) {
    if (!confirm(`Delete room "${room.name}"?`)) return;
    try {
      await api.delete(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}`);
      if (selectedRoomId === room.id) selectedRoomId = null;
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  async function cycleState(room) {
    const idx = STATES.indexOf(room.state);
    const next = STATES[(idx + 1) % STATES.length];
    try {
      await api.post(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}/state?state=${next}`);
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  async function revealItem(room, itemIndex) {
    try {
      await api.post(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}/reveal/${itemIndex}`);
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  // Send room monsters to referee panel via localStorage
  function sendToRefereePanel(room) {
    const monstersToSend = (room.monsters || []).map(m => ({
      monsterId: m.monster_id,
      quantity: m.quantity,
    }));
    localStorage.setItem(`referee_load_monsters_${campaignId}`, JSON.stringify(monstersToSend));
    goto(`/campaigns/${campaignId}/referee`);
  }

  // Move a room item to the party stash
  async function takeItemToStash(room, itemIndex) {
    const item = room.items[itemIndex];
    try {
      // Add to campaign stash
      await api.post(`/campaigns/${campaignId}/stash`, {
        item_id: item.item_id,
        quantity: item.quantity,
      });
      // Remove from room
      const updatedItems = [...room.items];
      updatedItems.splice(itemIndex, 1);
      await api.patch(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}`, {
        items: updatedItems,
      });
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  // Collect a single currency stash to party treasury
  async function collectCurrencyStash(room, stashIndex) {
    const stash = (room.currency || [])[stashIndex];
    if (!stash) return;
    try {
      await api.post(`/campaigns/${campaignId}/treasury`, {
        cp: stash.cp || 0,
        sp: stash.sp || 0,
        ep: stash.ep || 0,
        gp: stash.gp || 0,
        pp: stash.pp || 0,
      });
      // Remove this stash from room
      const updated = [...(room.currency || [])];
      updated.splice(stashIndex, 1);
      await api.patch(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}`, {
        currency: updated,
      });
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  async function revealCurrencyStash(room, stashIndex) {
    try {
      await api.post(`/campaigns/${campaignId}/dungeons/${dungeonId}/rooms/${room.id}/reveal-currency/${stashIndex}`);
      await reload();
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Dungeon editing ---
  function openDungeonEditor() {
    dungeonEditName = dungeon.name;
    dungeonEditDesc = dungeon.description || '';
    dungeonEditSections = (dungeon.sections || []).map(s => ({
      ...s,
      wandering_monsters: [...(s.wandering_monsters || [])],
    }));
    showDungeonEditor = true;
  }

  function addSection() {
    dungeonEditSections = [...dungeonEditSections, {
      name: '',
      encounter_chance: 1,
      check_interval: 2,
      wandering_monsters: [],
    }];
  }

  function removeSection(idx) {
    dungeonEditSections = dungeonEditSections.filter((_, i) => i !== idx);
  }

  function addWanderingMonster(sectionIdx) {
    dungeonEditSections[sectionIdx].wandering_monsters = [
      ...dungeonEditSections[sectionIdx].wandering_monsters,
      { monster_id: null, name: '', quantity_dice: '1d4', weight: 1 },
    ];
    dungeonEditSections = dungeonEditSections;
  }

  function removeWanderingMonster(sectionIdx, monsterIdx) {
    dungeonEditSections[sectionIdx].wandering_monsters =
      dungeonEditSections[sectionIdx].wandering_monsters.filter((_, i) => i !== monsterIdx);
    dungeonEditSections = dungeonEditSections;
  }

  async function saveDungeonEdit() {
    try {
      // Fill monster names from the monster list
      for (const section of dungeonEditSections) {
        for (const wm of section.wandering_monsters) {
          if (wm.monster_id) {
            const mon = monsters.find(m => m.id === parseInt(wm.monster_id));
            if (mon) wm.name = mon.name;
          }
        }
      }
      await api.patch(`/campaigns/${campaignId}/dungeons/${dungeonId}`, {
        name: dungeonEditName.trim(),
        description: dungeonEditDesc.trim() || null,
        sections: dungeonEditSections,
      });
      await reload();
      showDungeonEditor = false;
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Wandering monster roll ---
  async function rollWanderingMonster() {
    if (!rollDice || !currentSectionData) return;
    const chance = currentSectionData.encounter_chance || 1;
    const total = await rollDice('1d6', (roll) => {
      const encounter = roll <= chance;
      return {
        display: roll,
        text: encounter
          ? `Wandering Monster! (${roll} vs ${chance}-in-6, ${currentSection})`
          : `No encounter (${roll} vs ${chance}-in-6, ${currentSection})`,
      };
    });
    if (total != null && total <= chance) {
      // Roll on the table using weighted random
      const table = currentSectionData.wandering_monsters || [];
      if (table.length > 0) {
        const totalWeight = table.reduce((s, m) => s + (m.weight || 1), 0);
        let roll = Math.random() * totalWeight;
        let picked = table[0];
        for (const entry of table) {
          roll -= (entry.weight || 1);
          if (roll <= 0) { picked = entry; break; }
        }
        wanderingMonsterResult = picked;
        rolledQuantity = null;
        reactionResult = null;
      }
    }
  }

  let wanderingMonsterResult = null;
  let rolledQuantity = null;
  let reactionResult = null;
  let showEncounterTable = false;

  const REACTION_TABLE = [
    { max: 2, result: 'Hostile, attacks', color: 'text-red-900' },
    { max: 5, result: 'Unfriendly, may attack', color: 'text-orange-800' },
    { max: 8, result: 'Neutral, uncertain', color: 'text-ink' },
    { max: 11, result: 'Indifferent, uninterested', color: 'text-blue-800' },
    { max: 99, result: 'Friendly, helpful', color: 'text-green-800' },
  ];

  function getReaction(roll) {
    return REACTION_TABLE.find(r => roll <= r.max) || REACTION_TABLE[2];
  }

  async function rollQuantity() {
    if (!rollDice || !wanderingMonsterResult) return;
    const dice = wanderingMonsterResult.quantity_dice || '1';
    const total = await rollDice(dice, (roll) => {
      return { display: roll, text: `${wanderingMonsterResult.name}: ${roll} appearing` };
    });
    if (total != null) {
      rolledQuantity = total;
    }
  }

  async function rollReaction() {
    if (!rollDice) return;
    const total = await rollDice('2d6', (roll) => {
      const reaction = getReaction(roll);
      return { display: roll, text: `Reaction: ${reaction.result}` };
    });
    if (total != null) {
      reactionResult = getReaction(total);
      reactionResult.roll = total;
    }
  }

  async function sendWanderingToPanel() {
    if (!wanderingMonsterResult) return;
    const entry = wanderingMonsterResult;

    // Use already-rolled quantity, or roll now
    let qty = rolledQuantity;
    if (!qty && rollDice) {
      const dice = entry.quantity_dice || '1';
      qty = await rollDice(dice, (roll) => {
        return { display: roll, text: `${entry.name}: ${roll} appearing` };
      });
    }
    if (!qty || qty <= 0) qty = 1;

    localStorage.setItem(`referee_load_monsters_${campaignId}`, JSON.stringify([{
      monsterId: entry.monster_id,
      quantity: qty,
    }]));
    wanderingMonsterResult = null;
    reactionResult = null;
    rolledQuantity = null;
    goto(`/campaigns/${campaignId}/referee`);
  }

  // Room editor helpers
  function addMonster() { roomForm.monsters = [...roomForm.monsters, { monster_id: null, quantity: 1 }]; }
  function removeMonster(i) { roomForm.monsters = roomForm.monsters.filter((_, idx) => idx !== i); }
  function addItem() { roomForm.items = [...roomForm.items, { item_id: null, quantity: 1, hidden: false, search_chance: null }]; }
  function removeItem(i) { roomForm.items = roomForm.items.filter((_, idx) => idx !== i); }
  function addTrap() { roomForm.traps = [...roomForm.traps, { name: '', trigger: '', damage_dice: '', save_type: '', save_target: null, description: '' }]; }
  function removeTrap(i) { roomForm.traps = roomForm.traps.filter((_, idx) => idx !== i); }
  function addExit() { roomForm.exits = [...roomForm.exits, { direction: '', description: '', locked: false, key_hint: '' }]; }
  function removeExit(i) { roomForm.exits = roomForm.exits.filter((_, idx) => idx !== i); }

  function monsterName(id) {
    return monsters.find(m => m.id === id)?.name ?? `Monster #${id}`;
  }

  function itemName(id) {
    return items.find(i => i.id === id)?.name ?? `Item #${id}`;
  }

  async function rollTrapDamage(trap) {
    if (!rollDice || !trap.damage_dice) return;
    await rollDice(trap.damage_dice, (total) => {
      return { display: total, text: `${trap.name}: ${total} damage` };
    });
  }
</script>

<svelte:head>
  <title>{dungeon?.name ?? 'Dungeon'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading...</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if dungeon}
  <DiceOverlay bind:roll={rollDice} />
  <PageWrapper title={dungeon.name} maxWidth="max-w-7xl">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <a href="/campaigns/{campaignId}" class="text-xs text-ink-faint hover:text-ink">&larr; {campaign?.name ?? 'Campaign'}</a>
        {#if dungeon.description}
          <p class="text-sm text-ink-faint mt-1">{dungeon.description}</p>
        {/if}
      </div>
      {#if isGM}
        <div class="flex items-center gap-2">
          {#if sectionNames.length > 0}
            <select class="input text-xs py-0.5" bind:value={currentSection}>
              {#each sectionNames as name}
                <option value={name}>{name}</option>
              {/each}
            </select>
            {#if currentSectionData}
              <button class="btn text-xs" on:click={rollWanderingMonster} disabled={!rollDice}>Roll Wandering</button>
              <button class="btn-ghost text-xs" on:click={() => showEncounterTable = !showEncounterTable}>
                {showEncounterTable ? 'Hide Table' : 'View Table'}
              </button>
            {/if}
          {/if}
          <button class="btn-ghost text-xs" on:click={openDungeonEditor}>Edit Dungeon</button>
          <button class="btn text-xs" on:click={openAddRoom}>+ Add Room</button>
        </div>
      {/if}
    </div>

    <!-- Dungeon Time Widget -->
    {#if isGM}
      <DungeonTimeWidget {campaignId} {rollDice} />
    {/if}

    <!-- Encounter Table -->
    {#if showEncounterTable && currentSectionData}
      <div class="panel mb-4">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-xs text-ink-faint uppercase tracking-wide">
            {currentSection} — Wandering Monsters ({currentSectionData.encounter_chance}-in-6, every {currentSectionData.check_interval} turns)
          </h3>
          <button class="btn-ghost text-xs" on:click={() => showEncounterTable = false}>Hide</button>
        </div>
        {#if (currentSectionData.wandering_monsters || []).length > 0}
          {@const totalWeight = currentSectionData.wandering_monsters.reduce((s, m) => s + (m.weight || 1), 0)}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-ink-faint/30 text-xs text-ink-faint">
                <th class="text-left py-1">Monster</th>
                <th class="text-center py-1">Qty</th>
                <th class="text-center py-1">Chance</th>
              </tr>
            </thead>
            <tbody>
              {#each currentSectionData.wandering_monsters as wm}
                <tr class="border-b border-parchment-200 last:border-0">
                  <td class="py-1 text-ink">{wm.name || `Monster #${wm.monster_id}`}</td>
                  <td class="py-1 text-center text-ink-faint">{wm.quantity_dice}</td>
                  <td class="py-1 text-center text-ink-faint">{Math.round(((wm.weight || 1) / totalWeight) * 100)}%</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <p class="text-xs text-ink-faint">No wandering monsters defined for this section.</p>
        {/if}
      </div>
    {/if}

    <!-- Wandering Monster Result -->
    {#if wanderingMonsterResult}
      <div class="panel bg-red-50 border-red-400 mb-4">
        <div class="flex items-center justify-between mb-1">
          <div>
            <span class="text-sm font-medium text-red-900">Wandering Monster: {wanderingMonsterResult.name}</span>
            {#if rolledQuantity}
              <span class="text-sm font-medium text-red-900 ml-2">x{rolledQuantity}</span>
            {:else}
              <span class="text-xs text-red-700 ml-2">({wanderingMonsterResult.quantity_dice})</span>
            {/if}
          </div>
          <button class="btn-ghost text-xs" on:click={() => { wanderingMonsterResult = null; reactionResult = null; rolledQuantity = null; }}>Dismiss</button>
        </div>
        {#if reactionResult}
          <div class="text-sm mb-2">
            <span class="font-medium {reactionResult.color}">Reaction ({reactionResult.roll}): {reactionResult.result}</span>
          </div>
        {/if}
        <div class="flex gap-2">
          <button class="btn-ghost text-xs" on:click={rollQuantity} disabled={!rollDice}>Roll Qty ({wanderingMonsterResult.quantity_dice})</button>
          <button class="btn-ghost text-xs" on:click={rollReaction} disabled={!rollDice}>Roll Reaction (2d6)</button>
          <button class="btn text-xs" on:click={sendWanderingToPanel}>Send to Referee Panel</button>
        </div>
      </div>
    {/if}

    {#if rooms.length === 0}
      <div class="panel text-center py-8">
        <p class="text-ink-faint">No rooms yet. {isGM ? 'Click "+ Add Room" to start building.' : ''}</p>
      </div>
    {:else}
      <!-- Split view: room list + detail -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Room list sidebar -->
        <div class="lg:col-span-3 space-y-1">
          {#each roomsBySection as group}
            {#if sectionNames.length > 0}
              <div class="text-[10px] text-ink-faint uppercase tracking-wide px-3 pt-2 pb-1 font-medium {currentSection === group.name ? 'text-ink' : ''}">
                {group.label}
              </div>
            {/if}
            {#each group.rooms as room (room.id)}
              <button
                class="w-full text-left px-3 py-2 rounded text-sm transition-colors
                  {selectedRoomId === room.id ? 'bg-parchment-100 border border-ink-faint/30' : 'hover:bg-parchment-100/50'}"
                on:click={() => selectedRoomId = room.id}
              >
                <div class="flex items-center gap-2">
                  <span class="font-serif text-ink font-medium w-6 text-right shrink-0">{room.room_number}.</span>
                  <span class="text-ink truncate flex-1">{room.name}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded {STATE_COLORS[room.state]}">{STATE_LABELS[room.state]}</span>
                </div>
              </button>
            {/each}
          {/each}
        </div>

        <!-- Room detail -->
        <div class="lg:col-span-9">
          {#if selectedRoom}
            <div class="panel">
              <!-- Room header -->
              <div class="flex items-start justify-between mb-4">
                <div>
                  <h2 class="font-serif text-2xl text-ink">
                    {selectedRoom.room_number}. {selectedRoom.name}
                  </h2>
                  <button
                    class="text-xs px-2 py-0.5 rounded mt-1 {STATE_COLORS[selectedRoom.state]} cursor-pointer"
                    on:click={() => isGM && cycleState(selectedRoom)}
                    title={isGM ? 'Click to cycle state' : ''}
                  >{STATE_LABELS[selectedRoom.state]}</button>
                </div>
                {#if isGM}
                  <div class="flex gap-2">
                    {#if (selectedRoom.monsters || []).length > 0}
                      <button class="btn text-xs" on:click={() => sendToRefereePanel(selectedRoom)}>
                        Send to Referee Panel
                      </button>
                    {/if}
                    <button class="btn-ghost text-xs" on:click={() => openEditRoom(selectedRoom)}>Edit</button>
                    <button class="btn-danger text-xs" on:click={() => deleteRoom(selectedRoom)}>Delete</button>
                  </div>
                {/if}
              </div>

              <!-- Description -->
              {#if selectedRoom.description}
                <div class="text-sm text-ink mb-4">
                  <Markdown text={selectedRoom.description} />
                </div>
              {/if}

              <!-- Exits -->
              {#if (selectedRoom.exits || []).length > 0}
                <div class="mb-4">
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Exits</h3>
                  <div class="space-y-1">
                    {#each selectedRoom.exits as exit}
                      <div class="text-sm">
                        <span class="font-medium text-ink">{exit.direction}:</span>
                        <span class="text-ink-faint">{exit.description || ''}</span>
                        {#if exit.locked}<Badge label="Locked" />{/if}
                        {#if exit.key_hint && isGM}<span class="text-xs text-amber-700 ml-1">({exit.key_hint})</span>{/if}
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Monsters -->
              {#if (selectedRoom.monsters || []).length > 0}
                <div class="mb-4">
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Monsters</h3>
                  <div class="space-y-1">
                    {#each selectedRoom.monsters as m}
                      <div class="text-sm text-ink">
                        {monsterName(m.monster_id)} x{m.quantity}
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Traps -->
              {#if (selectedRoom.traps || []).length > 0}
                <div class="mb-4">
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Traps</h3>
                  <div class="space-y-2">
                    {#each selectedRoom.traps as trap}
                      <div class="text-sm border border-red-200 rounded p-2 bg-red-50/30">
                        <div class="font-medium text-ink">{trap.name}</div>
                        {#if trap.trigger}<div class="text-xs text-ink-faint">Trigger: {trap.trigger}</div>{/if}
                        {#if trap.description}<div class="text-xs text-ink-faint">{trap.description}</div>{/if}
                        <div class="flex gap-3 mt-1 text-xs">
                          {#if trap.damage_dice}
                            <button
                              class="text-red-700 hover:underline cursor-pointer"
                              on:click={() => rollTrapDamage(trap)}
                            >Damage: {trap.damage_dice}</button>
                          {/if}
                          {#if trap.save_type}
                            <span class="text-ink-faint">Save: {trap.save_type}{trap.save_target ? ` (${trap.save_target}+)` : ''}</span>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Items -->
              {#if (selectedRoom.items || []).length > 0}
                <div class="mb-4">
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Items</h3>
                  <div class="space-y-1">
                    {#each selectedRoom.items as item, idx}
                      <div class="flex items-center justify-between text-sm">
                        <div>
                          {#if item.hidden}
                            {#if isGM}
                              <span class="text-ink-faint italic">{itemName(item.item_id)} x{item.quantity}</span>
                              <Badge label="Hidden" variant="gm" />
                              {#if item.search_chance}
                                <span class="text-xs text-ink-faint">({item.search_chance}-in-6)</span>
                              {/if}
                            {/if}
                          {:else}
                            <span class="text-ink">{itemName(item.item_id)} x{item.quantity}</span>
                          {/if}
                        </div>
                        <div class="flex gap-1">
                          {#if isGM && item.hidden}
                            <button class="btn-ghost text-xs" on:click={() => revealItem(selectedRoom, idx)}>Reveal</button>
                          {/if}
                          {#if isGM && !item.hidden}
                            <button class="btn text-xs" on:click={() => takeItemToStash(selectedRoom, idx)}>To Stash</button>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Currency Stashes -->
              {#if (selectedRoom.currency || []).length > 0}
                <div class="mb-4">
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Currency</h3>
                  <div class="space-y-2">
                    {#each selectedRoom.currency as stash, idx}
                      {#if stash.hidden}
                        {#if isGM}
                          <div class="flex items-center justify-between text-sm border border-parchment-200 rounded p-2 opacity-60">
                            <div>
                              <span class="text-ink-faint italic">{stash.description || 'Hidden coins'}</span>
                              <Badge label="Hidden" variant="gm" />
                              {#if stash.search_chance}
                                <span class="text-xs text-ink-faint">({stash.search_chance}-in-6)</span>
                              {/if}
                            </div>
                            <button class="btn-ghost text-xs" on:click={() => revealCurrencyStash(selectedRoom, idx)}>Reveal</button>
                          </div>
                        {/if}
                      {:else}
                        <div class="border border-parchment-200 rounded p-2">
                          {#if stash.description}
                            <div class="text-xs text-ink-faint mb-1">{stash.description}</div>
                          {/if}
                          <div class="flex flex-wrap gap-3 items-center">
                            {#each [['pp','PP'],['gp','GP'],['ep','EP'],['sp','SP'],['cp','CP']] as [key, label]}
                              {#if (stash[key] || 0) > 0}
                                <div class="text-center">
                                  <div class="font-serif text-lg text-ink">{stash[key].toLocaleString()}</div>
                                  <div class="text-xs text-ink-faint">{label}</div>
                                </div>
                              {/if}
                            {/each}
                            {#if isGM}
                              <button class="btn text-xs ml-auto" on:click={() => collectCurrencyStash(selectedRoom, idx)}>Collect</button>
                            {/if}
                          </div>
                        </div>
                      {/if}
                    {/each}
                  </div>
                </div>
              {/if}


              <!-- Notes -->
              {#if selectedRoom.notes}
                <div>
                  <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-1">Notes</h3>
                  <div class="text-sm text-ink-faint">
                    <Markdown text={selectedRoom.notes} />
                  </div>
                </div>
              {/if}
            </div>
          {:else}
            <div class="panel text-center py-8">
              <p class="text-ink-faint">Select a room from the list.</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </PageWrapper>
{/if}

<!-- Room Editor Modal -->
<Modal bind:open={showRoomEditor} title={editingRoom ? `Edit Room ${editingRoom.room_number}` : 'New Room'} maxWidth="max-w-3xl">
  <div class="space-y-4 max-h-[70vh] overflow-y-auto">
    <!-- Basic info -->
    <div class="grid grid-cols-6 gap-3">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="rm-num">#</label>
        <input id="rm-num" class="input w-full" type="number" min="1" bind:value={roomForm.room_number} />
      </div>
      <div class="col-span-3">
        <label class="block text-xs text-ink-faint mb-1" for="rm-name">Name</label>
        <input id="rm-name" class="input w-full" type="text" bind:value={roomForm.name} placeholder="Guard Room" />
      </div>
      <div class="col-span-2">
        <label class="block text-xs text-ink-faint mb-1" for="rm-section">Section</label>
        <select id="rm-section" class="input w-full" bind:value={roomForm.section}>
          <option value="">None</option>
          {#each sectionNames as name}
            <option value={name}>{name}</option>
          {/each}
        </select>
      </div>
    </div>

    <div>
      <label class="block text-xs text-ink-faint mb-1" for="rm-desc">Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="rm-desc" class="input w-full resize-y font-mono text-sm" rows="6" bind:value={roomForm.description} placeholder="What the characters see when they enter..."></textarea>
    </div>

    <div>
      <label class="block text-xs text-ink-faint mb-1" for="rm-notes">Notes</label>
      <textarea id="rm-notes" class="input w-full resize-none text-sm" rows="2" bind:value={roomForm.notes} placeholder="GM notes..."></textarea>
    </div>

    <!-- Currency Stashes -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs text-ink-faint uppercase tracking-wide">Currency</span>
        <button type="button" class="btn-ghost text-xs" on:click={() => roomForm.currency = [...roomForm.currency, { description: '', cp: 0, sp: 0, ep: 0, gp: 0, pp: 0, hidden: false, search_chance: null }]}>+ Add</button>
      </div>
      {#each roomForm.currency as stash, i}
        <div class="border border-parchment-200 rounded p-2 mb-2 space-y-1">
          <div class="flex gap-2">
            <input class="input flex-1 text-sm" type="text" bind:value={stash.description} placeholder="Where are these coins? (e.g. 'in locked chest')" />
            <label class="flex items-center gap-1 text-xs text-ink-faint shrink-0">
              <input type="checkbox" bind:checked={stash.hidden} class="accent-ink" /> Hidden
            </label>
            {#if stash.hidden}
              <input class="input w-14 text-sm" type="number" min="1" max="6" bind:value={stash.search_chance} placeholder="X/6" />
            {/if}
            <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => roomForm.currency = roomForm.currency.filter((_, idx) => idx !== i)}>X</button>
          </div>
          <div class="flex flex-wrap gap-2">
            {#each [['cp','CP'],['sp','SP'],['ep','EP'],['gp','GP'],['pp','PP']] as [key, label]}
              <div class="flex flex-col items-center">
                <label class="text-[10px] text-ink-faint uppercase">{label}</label>
                <input class="input w-14 text-center text-sm" type="number" min="0" bind:value={stash[key]} />
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>

    <!-- Monsters -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs text-ink-faint uppercase tracking-wide">Monsters</span>
        <button type="button" class="btn-ghost text-xs" on:click={addMonster}>+ Add</button>
      </div>
      {#each roomForm.monsters as m, i}
        <div class="flex gap-2 items-end mb-1">
          <select class="input flex-1 text-sm" bind:value={m.monster_id}>
            <option value={null}>Select monster...</option>
            {#each monsters as mon}
              <option value={mon.id}>{mon.name}</option>
            {/each}
          </select>
          <input class="input w-16 text-sm" type="number" min="1" bind:value={m.quantity} placeholder="Qty" />
          <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeMonster(i)}>X</button>
        </div>
      {/each}
    </div>

    <!-- Items -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs text-ink-faint uppercase tracking-wide">Items</span>
        <button type="button" class="btn-ghost text-xs" on:click={addItem}>+ Add</button>
      </div>
      {#each roomForm.items as item, i}
        <div class="flex gap-2 items-end mb-1">
          <select class="input flex-1 text-sm" bind:value={item.item_id}>
            <option value={null}>Select item...</option>
            {#each items as it}
              <option value={it.id}>{it.name}</option>
            {/each}
          </select>
          <input class="input w-16 text-sm" type="number" min="1" bind:value={item.quantity} placeholder="Qty" />
          <label class="flex items-center gap-1 text-xs text-ink-faint shrink-0">
            <input type="checkbox" bind:checked={item.hidden} class="accent-ink" /> Hidden
          </label>
          {#if item.hidden}
            <input class="input w-14 text-sm" type="number" min="1" max="6" bind:value={item.search_chance} placeholder="X/6" title="Search chance (X-in-6)" />
          {/if}
          <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeItem(i)}>X</button>
        </div>
      {/each}
    </div>

    <!-- Traps -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs text-ink-faint uppercase tracking-wide">Traps</span>
        <button type="button" class="btn-ghost text-xs" on:click={addTrap}>+ Add</button>
      </div>
      {#each roomForm.traps as trap, i}
        <div class="border border-parchment-200 rounded p-2 mb-2 space-y-1">
          <div class="flex gap-2">
            <input class="input flex-1 text-sm" type="text" bind:value={trap.name} placeholder="Trap name" />
            <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeTrap(i)}>X</button>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <input class="input text-sm" type="text" bind:value={trap.trigger} placeholder="Trigger" />
            <input class="input text-sm" type="text" bind:value={trap.damage_dice} placeholder="Damage (e.g. 2d6)" />
            <div class="flex gap-1">
              <select class="input text-sm flex-1" bind:value={trap.save_type}>
                <option value="">No save</option>
                <option value="death">Death</option>
                <option value="wands">Wands</option>
                <option value="paralyze">Paralyze</option>
                <option value="breath">Breath</option>
                <option value="spells">Spells</option>
              </select>
              {#if trap.save_type}
                <input class="input w-12 text-sm" type="number" bind:value={trap.save_target} placeholder="DC" />
              {/if}
            </div>
          </div>
          <textarea class="input w-full text-sm resize-none" rows="1" bind:value={trap.description} placeholder="Effect description..."></textarea>
        </div>
      {/each}
    </div>

    <!-- Exits -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs text-ink-faint uppercase tracking-wide">Exits</span>
        <button type="button" class="btn-ghost text-xs" on:click={addExit}>+ Add</button>
      </div>
      {#each roomForm.exits as exit, i}
        <div class="flex gap-2 items-end mb-1">
          <input class="input w-20 text-sm" type="text" bind:value={exit.direction} placeholder="North" />
          <input class="input flex-1 text-sm" type="text" bind:value={exit.description} placeholder="Description..." />
          <label class="flex items-center gap-1 text-xs text-ink-faint shrink-0">
            <input type="checkbox" bind:checked={exit.locked} class="accent-ink" /> Locked
          </label>
          {#if exit.locked}
            <input class="input w-24 text-sm" type="text" bind:value={exit.key_hint} placeholder="Key hint" />
          {/if}
          <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeExit(i)}>X</button>
        </div>
      {/each}
    </div>
  </div>

  <div class="flex gap-3 mt-4 pt-3 border-t border-parchment-200">
    <button class="btn" on:click={saveRoom} disabled={!roomForm.name.trim()}>
      {editingRoom ? 'Save Changes' : 'Create Room'}
    </button>
    <button class="btn-ghost" on:click={() => showRoomEditor = false}>Cancel</button>
  </div>
</Modal>

<!-- Dungeon Edit Modal -->
<Modal bind:open={showDungeonEditor} title="Edit Dungeon" maxWidth="max-w-3xl">
  <div class="space-y-4 max-h-[70vh] overflow-y-auto">
    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="de-name">Dungeon Name</label>
        <input id="de-name" class="input w-full" type="text" bind:value={dungeonEditName} />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="de-desc">Description</label>
        <input id="de-desc" class="input w-full" type="text" bind:value={dungeonEditDesc} />
      </div>
    </div>

    <!-- Sections -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-ink">Sections & Wandering Monsters</span>
        <button type="button" class="btn-ghost text-xs" on:click={addSection}>+ Add Section</button>
      </div>

      {#each dungeonEditSections as section, si}
        <div class="border border-parchment-200 rounded p-3 mb-3 space-y-2">
          <div class="flex gap-2 items-end">
            <div class="flex-1">
              <label class="text-[10px] text-ink-faint uppercase">Section Name</label>
              <input class="input w-full text-sm" type="text" bind:value={section.name} placeholder="Level 1: Gatehouse" />
            </div>
            <div class="w-20">
              <label class="text-[10px] text-ink-faint uppercase">Chance</label>
              <input class="input w-full text-sm" type="number" min="1" max="6" bind:value={section.encounter_chance} title="X-in-6" />
            </div>
            <div class="w-20">
              <label class="text-[10px] text-ink-faint uppercase">Every</label>
              <input class="input w-full text-sm" type="number" min="1" bind:value={section.check_interval} title="Check every N turns" />
            </div>
            <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeSection(si)}>X</button>
          </div>

          <!-- Wandering monsters for this section -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] text-ink-faint uppercase">Wandering Monsters</span>
              <button type="button" class="btn-ghost text-[10px]" on:click={() => addWanderingMonster(si)}>+ Add</button>
            </div>
            {#each section.wandering_monsters as wm, wi}
              <div class="flex gap-2 items-end mb-1">
                <select class="input flex-1 text-sm" bind:value={wm.monster_id}>
                  <option value={null}>Select monster...</option>
                  {#each monsters as mon}
                    <option value={mon.id}>{mon.name}</option>
                  {/each}
                </select>
                <div class="w-16">
                  <input class="input w-full text-sm" type="text" bind:value={wm.quantity_dice} placeholder="2d4" title="Quantity dice" />
                </div>
                <div class="w-14">
                  <input class="input w-full text-sm" type="number" min="1" bind:value={wm.weight} placeholder="Wt" title="Weight (higher = more likely)" />
                </div>
                <button type="button" class="btn-danger text-[10px] px-1.5 py-0.5" on:click={() => removeWanderingMonster(si, wi)}>X</button>
              </div>
            {/each}
            {#if section.wandering_monsters.length === 0}
              <p class="text-[10px] text-ink-faint">No wandering monsters.</p>
            {/if}
          </div>
        </div>
      {/each}

      {#if dungeonEditSections.length === 0}
        <p class="text-xs text-ink-faint">No sections. Add sections to organize rooms and define wandering monster tables.</p>
      {/if}
    </div>
  </div>

  <div class="flex gap-3 mt-4 pt-3 border-t border-parchment-200">
    <button class="btn" on:click={saveDungeonEdit}>Save Dungeon</button>
    <button class="btn-ghost" on:click={() => showDungeonEditor = false}>Cancel</button>
  </div>
</Modal>
