<script>
  export let initialData = null;
  export let onSubmit;

  let key = initialData?.key || '';
  let name = initialData?.name || '';
  let wage = initialData?.wage ?? 100;
  let description = initialData?.description || '';

  let submitting = false;
  let error = '';

  function autoKey() {
    if (!key || key === initialData?.key) {
      key = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    }
  }

  async function handleSubmit() {
    if (!name.trim()) { error = 'Name is required.'; return; }
    if (!key.trim()) { error = 'Key is required.'; return; }

    submitting = true;
    error = '';
    try {
      await onSubmit({
        key: key.trim().toLowerCase().replace(/\s+/g, '_'),
        name: name.trim(),
        wage: parseInt(wage),
        description: description.trim() || null,
      });
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="st-name">Name</label>
        <input id="st-name" class="input w-full" type="text" bind:value={name} on:blur={autoKey} placeholder="Cartographer" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="st-key">Key</label>
        <input id="st-key" class="input w-full font-mono" type="text" bind:value={key} placeholder="cartographer" />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="st-wage">Monthly Wage <span class="text-ink-faint">(gp)</span></label>
      <input id="st-wage" class="input w-full" type="number" min="1" bind:value={wage} />
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="st-desc">Description</label>
      <textarea id="st-desc" class="input w-full resize-none" rows="3" bind:value={description} placeholder="What this specialist does..."></textarea>
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Specialist Type'}
    </button>
    <a href="/specialists" class="btn-ghost">Cancel</a>
  </div>
</div>
