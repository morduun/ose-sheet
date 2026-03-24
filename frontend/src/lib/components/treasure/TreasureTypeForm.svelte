<script>
  export let initialData = null;
  export let onSubmit;

  let key = initialData?.key || '';
  let name = initialData?.name || '';
  let category = initialData?.category || 'hoard';
  let averageGp = initialData?.average_gp ?? 0;
  let entriesJson = initialData?.entries
    ? JSON.stringify(initialData.entries, null, 2)
    : '[\n  {"type": "gp", "chance": 50, "dice": "1d6", "multiplier": 1000}\n]';

  let submitting = false;
  let error = '';

  function autoKey() {
    if (!key || key === initialData?.key) {
      key = name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '').slice(0, 5);
    }
  }

  async function handleSubmit() {
    if (!name.trim()) { error = 'Name is required.'; return; }
    if (!key.trim()) { error = 'Key is required.'; return; }

    let entries;
    try {
      entries = JSON.parse(entriesJson);
      if (!Array.isArray(entries)) throw new Error('Must be an array');
    } catch (e) {
      error = `Invalid entries JSON: ${e.message}`;
      return;
    }

    submitting = true;
    error = '';
    try {
      await onSubmit({
        key: key.trim().toUpperCase(),
        name: name.trim(),
        category,
        average_gp: parseInt(averageGp) || 0,
        entries,
      });
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div class="grid grid-cols-3 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="tt-name">Name</label>
        <input id="tt-name" class="input w-full" type="text" bind:value={name} on:blur={autoKey} placeholder="Type X" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="tt-key">Key</label>
        <input id="tt-key" class="input w-full font-mono" type="text" bind:value={key} placeholder="X" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="tt-cat">Category</label>
        <select id="tt-cat" class="input w-full" bind:value={category}>
          <option value="hoard">Hoard</option>
          <option value="individual">Individual</option>
          <option value="group">Group</option>
        </select>
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="tt-avg">Average GP Value</label>
      <input id="tt-avg" class="input w-48" type="number" min="0" bind:value={averageGp} />
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="tt-entries">
        Entries <span class="text-ink-faint">(JSON array — roll table definition)</span>
      </label>
      <textarea id="tt-entries" class="input w-full resize-none font-mono text-sm" rows="12" bind:value={entriesJson}></textarea>
      <details class="mt-1">
        <summary class="text-xs text-ink-faint cursor-pointer hover:text-ink">Entry format reference</summary>
        <div class="mt-1 bg-parchment-100 rounded p-2 text-xs font-mono space-y-0.5">
          <div><span class="text-ink font-medium">Coins:</span> {`{"type": "gp", "chance": 35, "dice": "2d6", "multiplier": 1000}`}</div>
          <div><span class="text-ink font-medium">Gems:</span> {`{"type": "gems", "chance": 50, "dice": "6d6"}`}</div>
          <div><span class="text-ink font-medium">Jewelry:</span> {`{"type": "jewelry", "chance": 50, "dice": "6d6"}`}</div>
          <div><span class="text-ink font-medium">Magic:</span> {`{"type": "magic", "chance": 30, "rolls": [{"count": 3, "table": "any"}]}`}</div>
          <div class="text-ink-faint mt-1">Tables: any, potion, scroll, sword, armor_shield, weapon, rod_staff_wand, ring, not_weapons, sword_armor_weapon</div>
          <div class="text-ink-faint">Individual types omit "chance" (always present)</div>
        </div>
      </details>
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Treasure Type'}
    </button>
    <a href="/treasure" class="btn-ghost">Cancel</a>
  </div>
</div>
