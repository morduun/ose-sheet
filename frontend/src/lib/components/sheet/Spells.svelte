<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';
  import Markdown from '$lib/components/shared/Markdown.svelte';

  export let character;

  let spellData = null;
  let loading = true;
  let error = '';

  // Arcane classes have a spellbook; divine can memorize any class spell
  const ARCANE = new Set(['Magic-User', 'Illusionist']);
  const DIVINE = new Set(['Cleric', 'Druid']);

  $: className = character.character_class?.name ?? '';
  $: isArcane = ARCANE.has(className);
  $: isDivine = DIVINE.has(className);
  $: isCaster = isArcane || isDivine;

  // Spell picker modal
  let showMemorizeModal = false;
  let memorizeLevel = 1;
  let availableForMemorize = [];
  let searchQuery = '';
  let addingSpell = null;

  // Expanded spell detail tracking
  let expandedSpells = new Set();

  function toggleSpell(id) {
    if (expandedSpells.has(id)) {
      expandedSpells.delete(id);
    } else {
      expandedSpells.add(id);
    }
    expandedSpells = expandedSpells;
  }

  // Add spell to spellbook (arcane only)
  let showAddSpellModal = false;
  let searchSpells = [];
  let spellSearch = '';
  let addingToBook = null;

  onMount(async () => {
    if (isCaster) await loadSpells();
    else loading = false;
  });

  async function loadSpells() {
    loading = true;
    try {
      spellData = await api.get(`/characters/${character.id}/spells`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  const ordinals = ['1st', '2nd', '3rd', '4th', '5th', '6th'];

  $: slotLevels = spellData
    ? ordinals.filter((o) => spellData.slots[o])
    : [];

  function memorizedByLevel(level) {
    if (!spellData) return [];
    return spellData.memorized.filter((m) => m.spell_level === ordinals.indexOf(level) + 1);
  }

  async function castSpell(memorizedId) {
    try {
      await api.post(`/characters/${character.id}/cast/${memorizedId}`, {});
      await loadSpells();
    } catch (e) {
      alert(e.message);
    }
  }

  async function rest() {
    try {
      await api.post(`/characters/${character.id}/rest`, {});
      await loadSpells();
    } catch (e) {
      alert(e.message);
    }
  }

  async function unmemorize(memorizedId) {
    try {
      await api.delete(`/characters/${character.id}/memorize/${memorizedId}`);
      await loadSpells();
    } catch (e) {
      alert(e.message);
    }
  }

  async function openMemorizeModal(level) {
    memorizeLevel = ordinals.indexOf(level) + 1;
    searchQuery = '';
    showMemorizeModal = true;

    try {
      if (isArcane) {
        // Pick from spellbook
        availableForMemorize = spellData.spellbook.filter((s) => s.level === memorizeLevel);
      } else {
        // Divine: any default spell of that level
        availableForMemorize = await api.get(
          `/spells/?spell_class=${encodeURIComponent(className.toLowerCase())}&level=${memorizeLevel}`
        );
      }
    } catch {
      availableForMemorize = [];
    }
  }

  $: filteredForMemorize = availableForMemorize.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  async function memorizeSpell(spell) {
    addingSpell = spell.id;
    try {
      await api.post(`/characters/${character.id}/memorize`, { spell_id: spell.id });
      await loadSpells();
      showMemorizeModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingSpell = null;
    }
  }

  // Spellbook add (arcane only)
  async function openAddSpellModal() {
    showAddSpellModal = true;
    spellSearch = '';
    try {
      searchSpells = await api.get(`/spells/?spell_class=${encodeURIComponent(className.toLowerCase())}`);
    } catch {
      searchSpells = [];
    }
  }

  $: filteredSearchSpells = searchSpells.filter((s) =>
    s.name.toLowerCase().includes(spellSearch.toLowerCase())
  );

  async function addToSpellbook(spell) {
    addingToBook = spell.id;
    try {
      await api.post(`/spells/${spell.id}/learn`, { character_id: character.id });
      await loadSpells();
      showAddSpellModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingToBook = null;
    }
  }

  async function removeFromSpellbook(spellId) {
    try {
      await api.delete(`/spells/${spellId}/forget/${character.id}`);
      await loadSpells();
    } catch (e) {
      alert(e.message);
    }
  }
</script>

{#if !isCaster}
  <div class="panel text-center py-8">
    <p class="text-ink-faint">This class does not cast spells.</p>
  </div>
{:else if loading}
  <p class="text-ink-faint">Loading spells…</p>
{:else if error}
  <p class="text-red-700">{error}</p>
{:else if spellData}
  <div class="space-y-6">

    <!-- Spellbook (arcane only) -->
    {#if isArcane}
      <div class="panel">
        <div class="flex items-center justify-between mb-4">
          <h2 class="section-title mb-0 border-none">Spellbook</h2>
          <button class="btn text-xs" on:click={openAddSpellModal}>+ Add Spell</button>
        </div>
        {#if spellData.spellbook.length === 0}
          <p class="text-ink-faint text-sm text-center py-4">No spells in spellbook.</p>
        {:else}
          <div class="space-y-1">
            {#each spellData.spellbook as spell}
              <div class="flex items-center justify-between border-b border-parchment-200 pb-1 last:border-0">
                <div>
                  <span class="text-sm text-ink">{spell.name}</span>
                  <span class="text-xs text-ink-faint ml-2">Lvl {spell.level}</span>
                </div>
                <button
                  class="btn-danger text-xs px-1.5 py-0.5"
                  on:click={() => removeFromSpellbook(spell.id)}
                >✕</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Memorized Spells by Level -->
    <div class="panel">
      <div class="flex items-center justify-between mb-4">
        <h2 class="section-title mb-0 border-none">Memorized Spells</h2>
        <button class="btn-ghost text-xs" on:click={rest}>Rest (restore all)</button>
      </div>

      {#if slotLevels.length === 0}
        <p class="text-ink-faint text-sm">No spell slots available at this level.</p>
      {:else}
        <div class="space-y-4">
          {#each slotLevels as level}
            {@const slot = spellData.slots[level]}
            {@const memorized = memorizedByLevel(level)}
            <div>
              <div class="flex items-center gap-3 mb-2">
                <span class="font-serif text-ink">{level} Level</span>
                <span class="text-xs text-ink-faint">
                  {slot.used}/{slot.total} used
                </span>
                <button
                  class="btn-ghost text-xs ml-auto"
                  on:click={() => openMemorizeModal(level)}
                >
                  + Memorize
                </button>
              </div>

              <!-- Slot indicators -->
              <div class="flex gap-1 mb-2">
                {#each Array(slot.total) as _, i}
                  <div
                    class="w-5 h-5 rounded-full border border-ink-faint"
                    class:bg-ink={i < slot.used}
                    class:bg-transparent={i >= slot.used}
                  ></div>
                {/each}
              </div>

              <div class="space-y-1">
                {#each memorized as entry}
                  {@const spell = entry.spell}
                  {@const isExpanded = expandedSpells.has(entry.id)}
                  <div
                    class="border border-parchment-200 rounded"
                    class:opacity-50={entry.cast}
                  >
                    <!-- Header row -->
                    <div class="flex items-center gap-2 px-2 py-1.5">
                      <button
                        class="flex-1 text-left flex items-center gap-2 min-w-0"
                        on:click={() => toggleSpell(entry.id)}
                      >
                        <span class="text-xs text-ink-faint select-none">{isExpanded ? '▾' : '▸'}</span>
                        <span class="text-sm text-ink font-medium truncate" class:line-through={entry.cast}>
                          {spell.name}
                        </span>
                        {#if spell.range}
                          <span class="text-xs text-ink-faint hidden sm:inline">{spell.range}</span>
                        {/if}
                        {#if spell.duration}
                          <span class="text-xs text-ink-faint hidden sm:inline">· {spell.duration}</span>
                        {/if}
                      </button>
                      <div class="flex gap-1 shrink-0">
                        {#if !entry.cast}
                          <button
                            class="btn text-xs px-2 py-0.5"
                            on:click={() => castSpell(entry.id)}
                          >Cast</button>
                        {/if}
                        <button
                          class="btn-danger text-xs px-1.5 py-0.5"
                          on:click={() => unmemorize(entry.id)}
                        >✕</button>
                      </div>
                    </div>

                    <!-- Expanded details -->
                    {#if isExpanded}
                      <div class="px-3 pb-2 border-t border-parchment-200 bg-parchment-50">
                        <!-- Stat line -->
                        <div class="flex flex-wrap gap-x-4 gap-y-1 py-1.5 text-xs">
                          {#if spell.range}
                            <span><span class="text-ink-faint">Range:</span> <strong>{spell.range}</strong></span>
                          {/if}
                          {#if spell.duration}
                            <span><span class="text-ink-faint">Duration:</span> <strong>{spell.duration}</strong></span>
                          {/if}
                          {#if spell.aoe}
                            <span><span class="text-ink-faint">Area:</span> <strong>{spell.aoe}</strong></span>
                          {/if}
                          {#if spell.save}
                            <span><span class="text-ink-faint">Save:</span> <strong>{spell.save}</strong></span>
                          {/if}
                        </div>
                        <!-- Description -->
                        {#if spell.description}
                          <div class="text-sm text-ink mt-1">
                            <Markdown text={spell.description} />
                          </div>
                        {/if}
                        <!-- Reversed form -->
                        {#if spell.reversed}
                          <div class="mt-2 pt-1.5 border-t border-parchment-200">
                            <span class="text-xs text-ink-faint font-medium">Reversed:</span>
                            <div class="text-sm text-ink mt-0.5">
                              <Markdown text={spell.reversed} />
                            </div>
                          </div>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Memorize Spell Modal -->
<Modal bind:open={showMemorizeModal} title="Memorize Spell">
  <div class="space-y-3">
    <input
      class="input w-full"
      type="text"
      placeholder="Search…"
      bind:value={searchQuery}
    />
    <div class="space-y-1 max-h-60 overflow-y-auto">
      {#each filteredForMemorize as spell}
        <button
          class="w-full text-left panel py-2 px-3 hover:bg-parchment-100 transition-colors"
          on:click={() => memorizeSpell(spell)}
          disabled={addingSpell === spell.id}
        >
          <div class="text-sm font-medium text-ink">{spell.name}</div>
          {#if spell.description}
            <div class="text-xs text-ink-faint line-clamp-2">{spell.description}</div>
          {/if}
        </button>
      {:else}
        <p class="text-ink-faint text-sm text-center py-4">No spells available.</p>
      {/each}
    </div>
  </div>
</Modal>

<!-- Add to Spellbook Modal -->
<Modal bind:open={showAddSpellModal} title="Add Spell to Spellbook">
  <div class="space-y-3">
    <input
      class="input w-full"
      type="text"
      placeholder="Search spells…"
      bind:value={spellSearch}
    />
    <div class="space-y-1 max-h-60 overflow-y-auto">
      {#each filteredSearchSpells as spell}
        <button
          class="w-full text-left panel py-2 px-3 hover:bg-parchment-100 transition-colors"
          on:click={() => addToSpellbook(spell)}
          disabled={addingToBook === spell.id}
        >
          <div class="text-sm font-medium text-ink">{spell.name}</div>
          <div class="text-xs text-ink-faint">Lvl {spell.level} · {spell.spell_class}</div>
        </button>
      {:else}
        <p class="text-ink-faint text-sm text-center py-4">No spells found.</p>
      {/each}
    </div>
  </div>
</Modal>
