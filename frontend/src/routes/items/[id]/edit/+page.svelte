<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import ItemForm from '$lib/components/items/ItemForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const itemId = $page.params.id;

  let item = null;
  let loading = true;
  let error = '';

  onMount(async () => {
    try {
      item = await api.get(`/items/${itemId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    // Strip fields that ItemUpdate doesn't accept
    const { is_default, campaign_id, ...updatePayload } = payload;
    await api.patch(`/items/${itemId}`, updatePayload);
    goto(`/items/${itemId}`);
  }
</script>

<svelte:head>
  <title>Edit {item?.name || 'Item'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit {item?.name || 'Item'}">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if item}
    <ItemForm
      initialData={item}
      onSubmit={handleSubmit}
    />
  {/if}
</PageWrapper>
