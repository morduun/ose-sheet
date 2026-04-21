<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import HexGrid from '$lib/components/campaign/HexGrid.svelte';
  import { TERRAIN_CATEGORIES, terrainLabel, terrainIcon } from '$lib/hex-terrain.js';

  const campaignId = $page.params.id;
  const mapId = $page.params.mapId;

  let campaign = null;
  let hexMap = null;
  let loading = true;
  let error = '';
  let isGM = false;

  // Tool state
  let mode = 'select'; // 'select', 'paint', 'erase', 'party'
  let activeTerrain = null;
  let activeCategory = null;
  let showPalette = false;
  let fogOfWar = false;
  let zoom = 1;

  // Selection state
  let selectedCol = null;
  let selectedRow = null;
  let selectedCell = null;

  // Cell edit form
  let cellName = '';
  let cellDescription = '';
  let cellNotes = '';
  let cellVisited = false;
  let saving = false;

  // POI form
  let poiType = 'settlement';
  let poiName = '';
  let poiDescription = '';
  let poiDungeonId = null;

  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch { return null; }
  }

  onMount(loadData);

  async function loadData() {
    loading = true;
    try {
      const userId = getUserId();
      campaign = await api.get(`/campaigns/${campaignId}`);
      isGM = campaign && userId && campaign.gm_id === userId;

      if (isGM) {
        hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      } else {
        hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}/player`);
        fogOfWar = true;
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function handleCellClick(e) {
    const { col, row, cell } = e.detail;

    if (!isGM) {
      // Player: just select
      selectCell(col, row, cell);
      return;
    }

    if (mode === 'paint' && activeTerrain) {
      await paintCell(col, row);
    } else if (mode === 'erase' && cell) {
      await eraseCell(cell);
    } else if (mode === 'party') {
      await moveParty(col, row);
    } else {
      selectCell(col, row, cell);
    }
  }

  function selectCell(col, row, cell) {
    selectedCol = col;
    selectedRow = row;
    selectedCell = cell || null;
    if (cell) {
      cellName = cell.name || '';
      cellDescription = cell.description || '';
      cellNotes = cell.notes || '';
      cellVisited = cell.visited || false;
    } else {
      cellName = '';
      cellDescription = '';
      cellNotes = '';
      cellVisited = false;
    }
  }

  async function paintCell(col, row) {
    try {
      await api.put(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/batch`, {
        cells: [{ col, row, terrain_type: activeTerrain }]
      });
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      // Re-select the cell to update the panel
      const updated = hexMap.cells.find(c => c.col === col && c.row === row);
      selectCell(col, row, updated);
    } catch (e) {
      alert(e.message);
    }
  }

  async function eraseCell(cell) {
    try {
      await api.delete(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/${cell.id}`);
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      selectedCell = null;
      selectedCol = null;
      selectedRow = null;
    } catch (e) {
      alert(e.message);
    }
  }

  async function moveParty(col, row) {
    try {
      hexMap = await api.post(`/campaigns/${campaignId}/hex-maps/${mapId}/party`, { col, row });
    } catch (e) {
      alert(e.message);
    }
  }

  async function saveCell() {
    if (!selectedCell) return;
    saving = true;
    try {
      await api.patch(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/${selectedCell.id}`, {
        name: cellName.trim() || null,
        description: cellDescription.trim() || null,
        notes: cellNotes.trim() || null,
        visited: cellVisited,
      });
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      const updated = hexMap.cells.find(c => c.id === selectedCell.id);
      selectedCell = updated;
    } catch (e) {
      alert(e.message);
    } finally {
      saving = false;
    }
  }

  async function toggleVisited() {
    if (!selectedCell) return;
    try {
      await api.post(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/${selectedCell.id}/visit`);
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      const updated = hexMap.cells.find(c => c.id === selectedCell.id);
      selectCell(updated.col, updated.row, updated);
    } catch (e) {
      alert(e.message);
    }
  }

  async function addPOI() {
    if (!selectedCell || !poiName.trim()) return;
    const pois = [...(selectedCell.pois || []), {
      type: poiType,
      name: poiName.trim(),
      description: poiDescription.trim() || null,
      linked_dungeon_id: poiDungeonId || null,
    }];
    try {
      await api.patch(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/${selectedCell.id}`, { pois });
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      const updated = hexMap.cells.find(c => c.id === selectedCell.id);
      selectCell(updated.col, updated.row, updated);
      poiName = '';
      poiDescription = '';
      poiDungeonId = null;
    } catch (e) {
      alert(e.message);
    }
  }

  async function removePOI(index) {
    if (!selectedCell) return;
    const pois = [...(selectedCell.pois || [])];
    pois.splice(index, 1);
    try {
      await api.patch(`/campaigns/${campaignId}/hex-maps/${mapId}/cells/${selectedCell.id}`, { pois });
      hexMap = await api.get(`/campaigns/${campaignId}/hex-maps/${mapId}`);
      const updated = hexMap.cells.find(c => c.id === selectedCell.id);
      selectCell(updated.col, updated.row, updated);
    } catch (e) {
      alert(e.message);
    }
  }

  function selectTerrain(key) {
    activeTerrain = key;
    mode = 'paint';
    showPalette = false;
  }

  function setMode(m) {
    mode = m;
    if (m !== 'paint') {
      showPalette = false;
    }
  }

  const POI_TYPES = ['settlement', 'dungeon', 'lair', 'landmark', 'resource', 'hazard'];
</script>

<svelte:head>
  <title>{hexMap?.name ?? 'Hex Map'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading...</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if hexMap}
  <PageWrapper>
    <!-- Breadcrumbs -->
    <nav class="text-xs text-ink-faint mb-4">
      <a href="/campaigns/{campaignId}" class="hover:underline">Campaign</a>
      <span class="mx-1">/</span>
      <span class="text-ink">{hexMap.name}</span>
      <span class="text-ink-faint ml-2">({hexMap.width}&times;{hexMap.height}, {hexMap.hex_size_miles} mi/hex)</span>
    </nav>

    {#if isGM}
      <!-- GM Toolbar -->
      <div class="panel mb-4 flex flex-wrap items-center gap-2">
        <button
          class={mode === 'select' ? 'btn text-xs' : 'btn-ghost text-xs'}
          on:click={() => setMode('select')}
          title="Select & edit cells"
        >Select</button>

        <div class="relative">
          <button
            class={mode === 'paint' ? 'btn text-xs' : 'btn-ghost text-xs'}
            on:click={() => { setMode('paint'); showPalette = !showPalette; }}
            title="Paint terrain"
          >
            Paint
            {#if activeTerrain}
              <img src={terrainIcon(activeTerrain)} alt="" class="inline w-4 h-4 ml-1 -mt-0.5" />
            {/if}
          </button>

          {#if showPalette}
            <div class="absolute top-full left-0 mt-1 z-50 bg-parchment border border-parchment-300 rounded shadow-lg p-3 w-80 max-h-96 overflow-y-auto">
              {#each TERRAIN_CATEGORIES as cat}
                <div class="mb-2">
                  <div class="text-[10px] uppercase tracking-wide text-ink-faint mb-1">{cat.name}</div>
                  <div class="flex flex-wrap gap-1">
                    {#each cat.terrains as t}
                      <button
                        class="w-9 h-8 rounded border {activeTerrain === t ? 'border-amber-600 ring-2 ring-amber-400' : 'border-parchment-300 hover:border-ink-faint'}"
                        on:click={() => selectTerrain(t)}
                        title={terrainLabel(t)}
                      >
                        <img src={terrainIcon(t)} alt={terrainLabel(t)} class="w-full h-full object-contain" />
                      </button>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <button
          class={mode === 'erase' ? 'btn text-xs' : 'btn-ghost text-xs'}
          on:click={() => setMode('erase')}
          title="Erase terrain"
        >Erase</button>

        <button
          class={mode === 'party' ? 'btn text-xs' : 'btn-ghost text-xs'}
          on:click={() => setMode('party')}
          title="Move party token"
        >Party</button>

        <div class="border-l border-parchment-300 h-6 mx-1"></div>

        <label class="text-xs text-ink-faint flex items-center gap-1">
          <input type="checkbox" bind:checked={fogOfWar} class="rounded" />
          Fog of War
        </label>

        <div class="border-l border-parchment-300 h-6 mx-1"></div>

        <button class="btn-ghost text-xs" on:click={() => zoom = Math.max(0.25, zoom - 0.25)}>-</button>
        <span class="text-xs text-ink-faint">{Math.round(zoom * 100)}%</span>
        <button class="btn-ghost text-xs" on:click={() => zoom = Math.min(3, zoom + 0.25)}>+</button>
      </div>
    {/if}

    <!-- Main content: Grid + Detail panel -->
    <div class="flex gap-4" style="min-height: 500px;">
      <!-- Hex Grid -->
      <div class="flex-1 min-w-0">
        <HexGrid
          width={hexMap.width}
          height={hexMap.height}
          cells={hexMap.cells}
          partyCol={hexMap.party_col}
          partyRow={hexMap.party_row}
          {selectedCol}
          {selectedRow}
          {fogOfWar}
          {zoom}
          on:cellclick={handleCellClick}
        />
        <p class="text-[10px] text-ink-faint mt-1">
          Hex icons by Thorfinn Tait &mdash; CC BY-NC-SA 4.0
        </p>
      </div>

      <!-- Detail Panel -->
      <div class="w-72 flex-shrink-0">
        {#if selectedCell}
          <div class="panel sticky top-4">
            <div class="flex items-center gap-2 mb-3">
              <img src={terrainIcon(selectedCell.terrain_type)} alt="" class="w-10 h-9" />
              <div>
                <div class="font-serif text-ink">{selectedCell.name || terrainLabel(selectedCell.terrain_type)}</div>
                <div class="text-[10px] text-ink-faint">({selectedCell.col}, {selectedCell.row}) &middot; {terrainLabel(selectedCell.terrain_type)}</div>
              </div>
            </div>

            {#if isGM}
              <!-- Editable form -->
              <div class="space-y-3 text-sm">
                <div>
                  <label class="block text-xs text-ink-faint mb-0.5">Name</label>
                  <input class="input w-full text-sm" type="text" bind:value={cellName} placeholder="Unnamed" />
                </div>
                <div>
                  <label class="block text-xs text-ink-faint mb-0.5">Description</label>
                  <textarea class="input w-full text-sm resize-none" rows="3" bind:value={cellDescription} placeholder="Visible to players..."></textarea>
                </div>
                <div>
                  <label class="block text-xs text-ink-faint mb-0.5">GM Notes</label>
                  <textarea class="input w-full text-sm resize-none" rows="3" bind:value={cellNotes} placeholder="Hidden from players..."></textarea>
                </div>
                <div class="flex items-center justify-between">
                  <label class="text-xs text-ink-faint flex items-center gap-1">
                    <input type="checkbox" bind:checked={cellVisited} class="rounded" />
                    Visited
                  </label>
                  <button class="btn-ghost text-xs" on:click={toggleVisited}>Toggle</button>
                </div>
                <button class="btn w-full text-xs" on:click={saveCell} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>

                <!-- POIs -->
                <div class="border-t border-parchment-200 pt-3">
                  <div class="text-xs text-ink-faint uppercase tracking-wide mb-2">Points of Interest</div>
                  {#if selectedCell.pois?.length > 0}
                    <ul class="space-y-1 mb-2">
                      {#each selectedCell.pois as poi, i}
                        <li class="flex items-start justify-between text-xs bg-parchment-100 rounded p-1.5">
                          <div>
                            <span class="font-medium text-ink">{poi.name}</span>
                            <span class="text-ink-faint ml-1">({poi.type})</span>
                            {#if poi.description}
                              <div class="text-ink-faint mt-0.5">{poi.description}</div>
                            {/if}
                          </div>
                          <button class="text-red-700 hover:text-red-900 ml-1" on:click={() => removePOI(i)} title="Remove">&times;</button>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                  <div class="space-y-1">
                    <select class="input w-full text-xs" bind:value={poiType}>
                      {#each POI_TYPES as pt}
                        <option value={pt}>{pt.charAt(0).toUpperCase() + pt.slice(1)}</option>
                      {/each}
                    </select>
                    <input class="input w-full text-xs" type="text" bind:value={poiName} placeholder="POI name..." />
                    <input class="input w-full text-xs" type="text" bind:value={poiDescription} placeholder="Description (optional)" />
                    <button class="btn-ghost text-xs w-full" on:click={addPOI} disabled={!poiName.trim()}>+ Add POI</button>
                  </div>
                </div>
              </div>
            {:else}
              <!-- Player view (read-only) -->
              {#if selectedCell.description}
                <p class="text-sm text-ink mt-2">{selectedCell.description}</p>
              {/if}
              {#if selectedCell.pois?.length > 0}
                <div class="mt-3 border-t border-parchment-200 pt-2">
                  <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Points of Interest</div>
                  <ul class="space-y-1">
                    {#each selectedCell.pois as poi}
                      <li class="text-xs">
                        <span class="font-medium">{poi.name}</span>
                        {#if poi.description}
                          <span class="text-ink-faint"> — {poi.description}</span>
                        {/if}
                      </li>
                    {/each}
                  </ul>
                </div>
              {/if}
            {/if}
          </div>
        {:else if selectedCol != null}
          <!-- Empty cell selected -->
          <div class="panel text-center text-sm text-ink-faint py-8">
            <p>Empty hex ({selectedCol}, {selectedRow})</p>
            {#if isGM}
              <p class="mt-2 text-xs">Select a terrain type and paint to fill this hex.</p>
            {/if}
          </div>
        {:else}
          <!-- Nothing selected -->
          <div class="panel text-center text-sm text-ink-faint py-8">
            <p>Click a hex to view details.</p>
            {#if isGM}
              <p class="mt-2 text-xs">Use the toolbar to paint terrain, move the party, or edit cells.</p>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </PageWrapper>
{/if}
