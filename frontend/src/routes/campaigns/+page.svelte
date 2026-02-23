<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';

  let campaigns = [];
  let loading = true;
  let error = '';
  let showJoin = false;
  let inviteCode = '';
  let joinError = '';
  let joining = false;

  // Decode JWT to get user id
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

  async function joinCampaign() {
    const code = inviteCode.trim();
    if (!code) {
      joinError = 'Please enter an invite code.';
      return;
    }
    joining = true;
    joinError = '';
    try {
      const campaign = await api.post('/campaigns/join', { invite_code: code });
      inviteCode = '';
      showJoin = false;
      goto(`/campaigns/${campaign.id}`);
    } catch (e) {
      joinError = e.message;
    } finally {
      joining = false;
    }
  }

  onMount(async () => {
    try {
      campaigns = await api.get('/campaigns/');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>Campaigns — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Campaigns">
  <div class="flex justify-between items-center mb-6">
    <p class="text-ink-faint text-sm">Your campaigns</p>
    <div class="flex gap-2">
      <button class="btn-ghost text-sm" on:click={() => (showJoin = !showJoin)}>
        Join Campaign
      </button>
      <a href="/campaigns/new" class="btn">+ New Campaign</a>
    </div>
  </div>

  {#if showJoin}
    <div class="panel mb-6">
      <h3 class="text-sm font-medium text-ink mb-2">Join with Invite Code</h3>
      <div class="flex gap-2 items-start">
        <input
          class="input flex-1"
          type="text"
          placeholder="Enter invite code"
          bind:value={inviteCode}
          on:keydown={(e) => e.key === 'Enter' && joinCampaign()}
        />
        <button class="btn" on:click={joinCampaign} disabled={joining}>
          {joining ? 'Joining…' : 'Join'}
        </button>
      </div>
      {#if joinError}
        <p class="text-red-700 text-xs mt-2">{joinError}</p>
      {/if}
    </div>
  {/if}

  {#if loading}
    <p class="text-ink-faint">Loading…</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if campaigns.length === 0}
    <div class="panel text-center py-8">
      <p class="text-ink-faint mb-4">No campaigns yet.</p>
      <a href="/campaigns/new" class="btn">Create your first campaign</a>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2">
      {#each campaigns as campaign}
        <a href="/campaigns/{campaign.id}" class="panel hover:bg-parchment-100 transition-colors block">
          <div class="flex items-start justify-between">
            <h2 class="font-serif text-xl text-ink">{campaign.name}</h2>
            <Badge
              label={campaign.gm_id === userId ? 'GM' : 'Player'}
              variant={campaign.gm_id === userId ? 'gm' : 'player'}
            />
          </div>
          {#if campaign.description}
            <p class="text-sm text-ink-light mt-1 line-clamp-2">{campaign.description}</p>
          {/if}
          <p class="text-xs text-ink-faint mt-2">
            {campaign.players?.length ?? 0} player{campaign.players?.length !== 1 ? 's' : ''}
          </p>
        </a>
      {/each}
    </div>
  {/if}
</PageWrapper>
