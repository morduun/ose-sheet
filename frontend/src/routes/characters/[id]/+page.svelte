<script>
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import CoreStats from '$lib/components/sheet/CoreStats.svelte';
  import ClassAbilities from '$lib/components/sheet/ClassAbilities.svelte';
  import SkillRolls from '$lib/components/sheet/SkillRolls.svelte';
  import Inventory from '$lib/components/sheet/Inventory.svelte';
  import Spells from '$lib/components/sheet/Spells.svelte';
  import Notes from '$lib/components/sheet/Notes.svelte';
  import Retainers from '$lib/components/sheet/Retainers.svelte';
  import Mercenaries from '$lib/components/sheet/Mercenaries.svelte';
  import DiceOverlay from '$lib/components/shared/DiceOverlay.svelte';

  $: characterId = $page.params.id;

  let character = null;
  let loading = true;
  let error = '';
  let activeTab = 'core';
  let rollDice = null;
  let loadedId = null;

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

  const userId = getUserId();
  $: isGM = character?.campaign?.gm_id === userId;
  $: isOwner = character?.user_id === userId;

  // Compute whether character has rollable skills (thief skills, turning, ability skill rolls, item skills)
  $: hasSkills = (() => {
    const cd = character?.character_class?.class_data ?? {};
    const lvlIdx = Math.max(0, (character?.level ?? 1) - 1);
    // Thief/class skills
    if (cd.thief_skills) {
      const hasClassSkills = Object.entries(cd.thief_skills).some(
        ([key, arr]) => key !== 'hear_noise' && Array.isArray(arr) && arr[Math.min(lvlIdx, arr.length - 1)] > 0
      );
      if (hasClassSkills) return true;
    }
    // Turn undead
    if (cd.turning) {
      const canTurn = Object.values(cd.turning).some((arr) => {
        if (!Array.isArray(arr)) return false;
        const val = arr[Math.min(lvlIdx, arr.length - 1)];
        return val !== '-' && val !== undefined;
      });
      if (canTurn) return true;
    }
    // Ability metadata skill rolls
    const meta = cd.ability_metadata ?? {};
    for (const m of Object.values(meta)) {
      if (m && m.type === 'skill') return true;
    }
    // Item skills
    if (character?.combat_stats?.item_skills?.length > 0) return true;
    return false;
  })();

  $: hasSpells = (character?.character_class?.class_data?.spell_lists?.length ?? 0) > 0;
  $: isPC = character?.character_type !== 'retainer';

  $: tabs = [
    { key: 'core', label: 'Core' },
    { key: 'abilities', label: 'Abilities' },
    ...(hasSkills ? [{ key: 'skills', label: 'Skills' }] : []),
    { key: 'inventory', label: 'Inventory' },
    ...(hasSpells ? [{ key: 'spells', label: 'Spells' }] : []),
    ...(isPC ? [{ key: 'retainers', label: 'Retainers' }] : []),
    ...(isPC ? [{ key: 'mercenaries', label: 'Mercenaries' }] : []),
    { key: 'notes', label: 'Notes' },
  ];

  async function loadCharacter(id) {
    loading = true;
    error = '';
    character = null;
    activeTab = 'core';
    try {
      character = await api.get(`/characters/${id}`);
      if (character.campaign_id) {
        try {
          const campaign = await api.get(`/campaigns/${character.campaign_id}`);
          character = { ...character, campaign };
        } catch {
          // campaign fetch failed — isGM will be false, breadcrumb shows fallback
        }
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  // Re-fetch when navigating between character pages (same route, different param)
  $: if (characterId && characterId !== loadedId) {
    loadedId = characterId;
    loadCharacter(characterId);
  }

  async function refreshCharacter() {
    try {
      const updated = await api.get(`/characters/${characterId}`);
      character = { ...updated, campaign: character?.campaign };
    } catch (e) {
      // silently fail — character data will be stale but not lost
    }
  }
</script>

<svelte:head>
  <title>{character?.name ?? 'Character Sheet'} — OSE Sheet</title>
</svelte:head>

<DiceOverlay bind:roll={rollDice} />

{#if loading}
  <div class="max-w-4xl mx-auto px-4 py-6">
    <p class="text-ink-faint">Loading…</p>
  </div>
{:else if error}
  <div class="max-w-4xl mx-auto px-4 py-6">
    <p class="text-red-700">{error}</p>
  </div>
{:else if character}
  <div class="max-w-4xl mx-auto px-4 py-6">
    <!-- Breadcrumb -->
    {#if character.campaign_id}
      <nav class="text-xs text-ink-faint mb-4 print:hidden">
        <a href="/campaigns" class="hover:text-ink">Campaigns</a>
        <span class="mx-1">›</span>
        <a href="/campaigns/{character.campaign_id}" class="hover:text-ink">
          {character.campaign?.name ?? 'Campaign'}
        </a>
        <span class="mx-1">›</span>
        {#if character.master_id}
          <a href="/characters/{character.master_id}" class="hover:text-ink">Master</a>
          <span class="mx-1">›</span>
        {/if}
        <span class="text-ink">{character.name}</span>
      </nav>
    {/if}

    <!-- Tab Bar -->
    <div class="flex border-b border-ink-faint mb-6 print:hidden overflow-x-auto">
      {#each tabs as tab}
        <button
          class={activeTab === tab.key ? 'tab-active' : 'tab'}
          on:click={() => (activeTab = tab.key)}
        >
          {tab.label}
        </button>
      {/each}
    </div>

    <!-- Tab Content -->
    {#if activeTab === 'core'}
      <CoreStats bind:character {isGM} {isOwner} {rollDice} />
    {:else if activeTab === 'abilities'}
      <ClassAbilities bind:character />
    {:else if activeTab === 'skills'}
      <SkillRolls {character} {rollDice} />
    {:else if activeTab === 'inventory'}
      <Inventory bind:character {isGM} on:ac-changed={refreshCharacter} />
    {:else if activeTab === 'spells'}
      <Spells bind:character />
    {:else if activeTab === 'retainers'}
      <Retainers bind:character {isGM} {isOwner} {rollDice} />
    {:else if activeTab === 'mercenaries'}
      <Mercenaries bind:character {isGM} {isOwner} {rollDice} />
    {:else if activeTab === 'notes'}
      <Notes bind:character />
    {/if}
  </div>
{/if}
