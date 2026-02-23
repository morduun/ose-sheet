<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import SpellForm from '$lib/components/spells/SpellForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const created = await api.post('/spells/', payload);
    goto(`/spells/${created.id}`);
  }
</script>

<svelte:head>
  <title>New Spell — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Spell">
  <SpellForm onSubmit={handleSubmit} />
</PageWrapper>
