<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import PartyStash from '$lib/components/campaign/PartyStash.svelte';
  import VehiclePanel from '$lib/components/campaign/VehiclePanel.svelte';

  const campaignId = $page.params.id;

  let campaign = null;
  let characters = [];
  let loading = true;
  let error = '';
  let copyFeedback = '';
  let userId = null;
  let graveyardOpen = true;
  let activeTab = 'adventurers';

  $: activeCharacters = characters.filter(c => c.status === 'active' || (!c.status && c.is_alive !== false));
  $: independentCharacters = characters.filter(c => c.status === 'independent');
  $: fallenCharacters = characters.filter(c => c.status === 'fallen' || (!c.status && c.is_alive === false));

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
  $: myCharacters = isGM ? activeCharacters : activeCharacters.filter(c => c.player_id === userId);

  onMount(async () => {
    userId = getUserId();
    try {
      [campaign, characters] = await Promise.all([
        api.get(`/campaigns/${campaignId}`),
        api.get(`/characters/?campaign_id=${campaignId}`),
      ]);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function copyInviteCode() {
    if (!campaign?.invite_code) return;
    await navigator.clipboard.writeText(campaign.invite_code);
    copyFeedback = 'Copied!';
    setTimeout(() => (copyFeedback = ''), 2000);
  }

  async function deleteCampaign() {
    if (!confirm(`Delete campaign "${campaign.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/campaigns/${campaignId}`);
      goto('/campaigns');
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<svelte:head>
  <title>{campaign?.name ?? 'Campaign'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading…</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if campaign}
  <PageWrapper title={campaign.name}>
    <!-- Invite code -->
    <div class="panel mb-6 flex flex-wrap items-center gap-3">
      <div>
        <span class="text-xs text-ink-faint uppercase tracking-wide">Invite Code</span>
        <div class="font-mono text-ink mt-0.5">{campaign.invite_code}</div>
      </div>
      <button class="btn-ghost text-xs" on:click={copyInviteCode}>
        {copyFeedback || 'Copy'}
      </button>
      {#if isGM}
        <div class="ml-auto flex gap-2">
          <a href="/campaigns/{campaignId}/referee" class="btn text-xs">Referee Panel</a>
          <a href="/campaigns/{campaignId}/referee/dungeon" class="btn text-xs">Dungeon Tracker</a>
          <a href="/campaigns/{campaignId}/referee/overland" class="btn text-xs">Overland Travel</a>
          <button class="btn-danger text-xs" on:click={deleteCampaign}>Delete Campaign</button>
        </div>
      {/if}
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6">
      <button
        class={activeTab === 'adventurers' ? 'tab-active' : 'tab'}
        on:click={() => (activeTab = 'adventurers')}
      >Adventurers</button>
      <button
        class={activeTab === 'stash' ? 'tab-active' : 'tab'}
        on:click={() => (activeTab = 'stash')}
      >Party Stash</button>
      <button
        class={activeTab === 'vehicles' ? 'tab-active' : 'tab'}
        on:click={() => (activeTab = 'vehicles')}
      >Vehicles</button>
    </div>

    {#if activeTab === 'adventurers'}
      <!-- Character roster — Living -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="section-title mb-0 border-none">Adventurers</h2>
        <a href="/campaigns/{campaignId}/characters/new" class="btn">+ New Character</a>
      </div>

      {#if activeCharacters.length === 0}
        <div class="panel text-center py-6">
          <p class="text-ink-faint text-sm mb-3">
            {fallenCharacters.length > 0 ? 'No active characters remain.' : 'No characters yet.'}
          </p>
          <a href="/campaigns/{campaignId}/characters/new" class="btn">Create a Character</a>
        </div>
      {:else}
        <div class="grid gap-3 sm:grid-cols-2">
          {#each activeCharacters as char}
            <a href="/characters/{char.id}" class="panel hover:bg-parchment-100 transition-colors block">
              <div class="flex items-start justify-between">
                <div>
                  <h3 class="font-serif text-lg text-ink">{char.name}</h3>
                  <p class="text-xs text-ink-faint mt-0.5">
                    {char.character_class?.name ?? char.combat_stats?.monster_name ?? 'Unknown'} · Level {char.level}
                  </p>
                </div>
                <Badge label={char.alignment ?? ''} />
              </div>
              <div class="flex gap-4 mt-2 text-xs text-ink-light">
                <span>HP {char.hp_current ?? '?'}/{char.hp_max ?? '?'}</span>
                <span>AC {char.ac ?? '?'}</span>
                <span>XP {char.xp ?? 0}</span>
              </div>
            </a>
          {/each}
        </div>
      {/if}

      <!-- Acting Independently -->
      {#if independentCharacters.length > 0}
        <details class="mt-6">
          <summary class="text-sm text-ink-faint cursor-pointer hover:text-ink select-none">
            Acting Independently ({independentCharacters.length})
          </summary>
          <div class="grid gap-3 sm:grid-cols-2 mt-3">
            {#each independentCharacters as char}
              <a
                href="/characters/{char.id}"
                class="panel hover:bg-parchment-100 transition-colors block opacity-75 border-l-4 border-ink-faint/30"
              >
                <div class="flex items-start justify-between">
                  <div>
                    <h3 class="font-serif text-lg text-ink">{char.name}</h3>
                    <p class="text-xs text-ink-faint mt-0.5">
                      {char.character_class?.name ?? char.combat_stats?.monster_name ?? 'Unknown'} · Level {char.level}
                    </p>
                  </div>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-ink/10 text-ink-faint uppercase tracking-wide font-medium">Independent</span>
                </div>
                <div class="flex gap-4 mt-2 text-xs text-ink-light">
                  <span>HP {char.hp_current ?? '?'}/{char.hp_max ?? '?'}</span>
                  <span>AC {char.ac ?? '?'}</span>
                  <span>XP {char.xp ?? 0}</span>
                </div>
              </a>
            {/each}
          </div>
        </details>
      {/if}

      <!-- Graveyard — Fallen Characters -->
      {#if fallenCharacters.length > 0}
        <div class="mt-8">
          <button
            class="flex items-center gap-2 w-full text-left mb-4"
            on:click={() => (graveyardOpen = !graveyardOpen)}
          >
            <span class="section-title mb-0 border-none text-ink-faint">The Fallen</span>
            <span class="text-xs text-ink-faint">{graveyardOpen ? '▾' : '▸'}</span>
            <span class="text-xs text-ink-faint">({fallenCharacters.length})</span>
          </button>

          {#if graveyardOpen}
            <div class="grid gap-3 sm:grid-cols-2">
              {#each fallenCharacters as char}
                <a
                  href="/characters/{char.id}"
                  class="panel hover:bg-parchment-100 transition-colors block opacity-60 border-l-4 border-red-900/40"
                >
                  <div class="flex items-start justify-between">
                    <div>
                      <h3 class="font-serif text-lg text-ink line-through decoration-1 text-ink-faint">{char.name}</h3>
                      <p class="text-xs text-ink-faint mt-0.5">
                        {char.character_class?.name ?? char.combat_stats?.monster_name ?? 'Unknown'} · Level {char.level}
                      </p>
                    </div>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-red-900/20 text-red-900 uppercase tracking-wide font-medium">Fallen</span>
                  </div>
                  <div class="flex gap-4 mt-2 text-xs text-ink-light">
                    <span>HP {char.hp_current ?? '?'}/{char.hp_max ?? '?'}</span>
                    <span>AC {char.ac ?? '?'}</span>
                    <span>XP {char.xp ?? 0}</span>
                  </div>
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Players list -->
      {#if campaign.players && campaign.players.length > 0}
        <div class="mt-6">
          <h2 class="section-title">Players</h2>
          <div class="flex flex-wrap gap-2">
            {#each campaign.players as player}
              <Badge label={player.name} variant="player" />
            {/each}
          </div>
        </div>
      {/if}
    {:else if activeTab === 'stash'}
      <PartyStash campaignId={campaignId} isGM={isGM} characters={myCharacters} />
    {:else if activeTab === 'vehicles'}
      <VehiclePanel campaignId={campaignId} isGM={isGM} characters={myCharacters} />
    {/if}
  </PageWrapper>
{/if}
