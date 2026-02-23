<script>
  import { ITEM_METADATA_TEMPLATES } from '$lib/item-metadata.js';

  /** Initial item data for edit mode (null for create) */
  export let initialData = null;
  /** Called with the assembled payload */
  export let onSubmit;

  const ITEM_TYPES = [
    'weapon', 'armor', 'ammo',
    'potion', 'scroll', 'ring', 'wand', 'wondrous',
    'consumable', 'tool', 'treasure',
  ];

  // --- Individual form fields (Svelte 5 reactivity safety) ---
  let name = initialData?.name || '';
  let itemType = initialData?.item_type || 'weapon';
  let equippable = initialData?.equippable || false;
  let weight = initialData?.weight != null ? String(initialData.weight) : '';
  let costGp = initialData?.cost_gp != null ? String(initialData.cost_gp) : '';
  let descriptionPlayer = initialData?.description_player || '';
  let descriptionGm = initialData?.description_gm || '';
  let metadataJson = initialData?.item_metadata
    ? JSON.stringify(initialData.item_metadata, null, 2)
    : formatTemplate(itemType);

  // Secrets — independent array of {text, revealed} objects
  let secretEntries = (initialData?.secrets || []).map(s => ({ text: s.text, revealed: s.revealed }));

  /** Format a template as pretty JSON, or empty string for empty objects */
  function formatTemplate(type) {
    const tmpl = ITEM_METADATA_TEMPLATES[type];
    if (!tmpl || Object.keys(tmpl).length === 0) return '';
    return JSON.stringify(tmpl, null, 2);
  }

  function onTypeChange() {
    // Only auto-populate if metadata is empty or matches a known template
    const trimmed = metadataJson.trim();
    const isTemplate = !trimmed || ITEM_TYPES.some(
      (t) => trimmed === JSON.stringify(ITEM_METADATA_TEMPLATES[t], null, 2)
    );
    if (isTemplate) {
      metadataJson = formatTemplate(itemType);
      equippable = ['weapon', 'armor', 'ammo'].includes(itemType);
    }
  }

  function addSecret() {
    secretEntries = [...secretEntries, { text: '', revealed: false }];
  }

  function removeSecret(index) {
    secretEntries = secretEntries.filter((_, i) => i !== index);
  }

  let submitting = false;
  let error = '';

  async function handleSubmit() {
    if (!name.trim()) { error = 'Item name is required.'; return; }

    // Validate JSON if provided
    let parsedMeta = null;
    if (metadataJson.trim()) {
      try {
        parsedMeta = JSON.parse(metadataJson.trim());
      } catch (e) {
        error = 'Item Metadata is not valid JSON.';
        return;
      }
    }

    submitting = true;
    error = '';

    try {
      const cleanedSecrets = secretEntries
        .filter(s => s.text.trim())
        .map(s => ({ text: s.text.trim(), revealed: s.revealed }));

      const payload = {
        name: name.trim(),
        item_type: itemType,
        equippable,
        weight: weight !== '' && weight != null ? parseFloat(weight) : null,
        cost_gp: costGp !== '' && costGp != null ? parseFloat(costGp) : null,
        description_player: descriptionPlayer.trim() || null,
        description_gm: descriptionGm.trim() || null,
        secrets: cleanedSecrets.length > 0 ? cleanedSecrets : null,
        item_metadata: parsedMeta,
      };

      await onSubmit(payload);
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div>
      <label class="block text-sm text-ink mb-1" for="item-name">Name</label>
      <input id="item-name" class="input w-full" type="text" bind:value={name} placeholder="Sword, Long" />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="item-type">Item Type</label>
        <select id="item-type" class="input w-full" bind:value={itemType} on:change={onTypeChange}>
          {#each ITEM_TYPES as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </div>
      <div class="flex items-end pb-2">
        <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
          <input type="checkbox" bind:checked={equippable} class="accent-ink" />
          Equippable
        </label>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="item-weight">Weight <span class="text-ink-faint">(coins)</span></label>
        <input id="item-weight" class="input w-full" type="number" step="any" bind:value={weight} placeholder="10" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="item-cost">Cost <span class="text-ink-faint">(GP)</span></label>
        <input id="item-cost" class="input w-full" type="number" step="any" bind:value={costGp} placeholder="25" />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-desc-player">Player Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="item-desc-player" class="input w-full resize-none" rows="4" bind:value={descriptionPlayer} placeholder="What players can see..."></textarea>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-desc-gm">GM Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="item-desc-gm" class="input w-full resize-none" rows="4" bind:value={descriptionGm} placeholder="Secret GM notes..."></textarea>
    </div>

    <!-- Revealable Secrets -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="block text-sm text-ink">Secrets <span class="text-ink-faint">(revealable to players)</span></label>
        <button type="button" class="btn-ghost text-xs" on:click={addSecret}>+ Add Secret</button>
      </div>
      {#if secretEntries.length > 0}
        <div class="space-y-2">
          {#each secretEntries as entry, i}
            <div class="flex gap-2 items-start border border-parchment-200 rounded p-2">
              <textarea
                class="input flex-1 resize-none text-sm"
                rows="2"
                placeholder="Secret text (e.g. 'This sword is +1')"
                bind:value={entry.text}
              ></textarea>
              <div class="flex flex-col items-center gap-1 shrink-0">
                <label class="flex items-center gap-1 text-xs text-ink-faint cursor-pointer" title="Revealed to players">
                  <input type="checkbox" bind:checked={entry.revealed} class="accent-ink" />
                  Shown
                </label>
                <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeSecret(i)}>Remove</button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-ink-faint">No secrets. Click "+ Add Secret" to add one.</p>
      {/if}
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-metadata">Item Metadata <span class="text-ink-faint">(JSON — damage_dice, ac, range, etc.)</span></label>
      <textarea id="item-metadata" class="input w-full resize-none font-mono text-sm" rows="5" bind:value={metadataJson} placeholder={'{"damage_dice": "1d8", "weapon_type": "melee"}'}></textarea>
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Item'}
    </button>
    <a href="/items" class="btn-ghost">Cancel</a>
  </div>
</div>
