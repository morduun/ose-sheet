<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  const typeId = $page.params.id;

  let st = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      st = await api.get(`/specialist-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function deleteType() {
    if (!confirm(`Delete ${st.name}?`)) return;
    try {
      await api.delete(`/specialist-types/${typeId}`);
      goto('/specialists');
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<svelte:head>
  <title>{st?.name ?? 'Specialist Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title={st?.name ?? 'Specialist Type'} maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if st}
    <div class="panel">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="font-serif text-3xl text-ink">{st.name}</h1>
          <p class="text-ink-faint text-sm mt-1">
            <span class="font-mono">{st.key}</span>
            {#if !st.is_default}
              · <Badge label="Custom" variant="gm" />
            {/if}
          </p>
        </div>
        <div class="text-right">
          <div class="text-xs text-ink-faint">Wage</div>
          <div class="font-serif text-3xl text-ink">{st.wage}</div>
          <div class="text-xs text-ink-faint">gp/month</div>
        </div>
      </div>

      {#if st.description}
        <p class="text-sm text-ink-light">{st.description}</p>
      {/if}
    </div>

    <div class="flex gap-3 mt-4">
      <a href="/specialists/{typeId}/edit" class="btn">Edit</a>
      <button class="btn-danger" on:click={deleteType}>Delete</button>
      <a href="/specialists" class="btn-ghost ml-auto">Back</a>
    </div>
  {/if}
</PageWrapper>
