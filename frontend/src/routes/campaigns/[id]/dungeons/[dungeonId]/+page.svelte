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
  $: selectedRoom = rooms.find(r => r.id === selectedRoomId) || null;

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
        <button class="btn text-xs" on:click={openAddRoom}>+ Add Room</button>
      {/if}
    </div>

    {#if rooms.length === 0}
      <div class="panel text-center py-8">
        <p class="text-ink-faint">No rooms yet. {isGM ? 'Click "+ Add Room" to start building.' : ''}</p>
      </div>
    {:else}
      <!-- Split view: room list + detail -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Room list sidebar -->
        <div class="lg:col-span-3 space-y-1">
          {#each rooms as room (room.id)}
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
    <div class="grid grid-cols-4 gap-3">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="rm-num">Number</label>
        <input id="rm-num" class="input w-full" type="number" min="1" bind:value={roomForm.room_number} />
      </div>
      <div class="col-span-3">
        <label class="block text-xs text-ink-faint mb-1" for="rm-name">Name</label>
        <input id="rm-name" class="input w-full" type="text" bind:value={roomForm.name} placeholder="Guard Room" />
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
