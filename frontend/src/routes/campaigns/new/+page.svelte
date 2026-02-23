<script>
  import { api } from '$lib/api.js';
  import { goto } from '$app/navigation';
  import PageWrapper from '$lib/components/PageWrapper.svelte';

  let name = '';
  let description = '';
  let submitting = false;
  let error = '';

  async function submit() {
    if (!name.trim()) {
      error = 'Campaign name is required.';
      return;
    }
    submitting = true;
    error = '';
    try {
      const campaign = await api.post('/campaigns/', {
        name: name.trim(),
        description: description.trim() || null,
      });
      goto(`/campaigns/${campaign.id}`);
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) submit();
  }
</script>

<svelte:head>
  <title>New Campaign — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Campaign">
  <div class="panel max-w-md">
    <div class="flex flex-col gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="name">Campaign Name</label>
        <input
          id="name"
          class="input w-full"
          type="text"
          placeholder="The Caves of Chaos"
          bind:value={name}
          on:keydown={onKeydown}
        />
      </div>

      <div>
        <label class="block text-sm text-ink mb-1" for="description">Description (optional)</label>
        <textarea
          id="description"
          class="input w-full resize-none"
          rows="3"
          placeholder="A brief description of your campaign…"
          bind:value={description}
        ></textarea>
      </div>

      {#if error}
        <p class="text-red-700 text-sm">{error}</p>
      {/if}

      <div class="flex gap-3">
        <button class="btn" on:click={submit} disabled={submitting}>
          {submitting ? 'Creating…' : 'Create Campaign'}
        </button>
        <a href="/campaigns" class="btn-ghost">Cancel</a>
      </div>
    </div>
  </div>
</PageWrapper>
