<script>
  /** Initial spell data for edit mode (null for create) */
  export let initialData = null;
  /** Called with the assembled payload */
  export let onSubmit;

  const SPELL_CLASSES = ['cleric', 'druid', 'illusionist', 'magic-user'];

  // --- Individual form fields (Svelte 5 reactivity safety) ---
  let name = initialData?.name || '';
  let spellClass = initialData?.spell_class || 'cleric';
  let level = initialData?.level || 1;
  let range = initialData?.range || '';
  let duration = initialData?.duration || '';
  let aoe = initialData?.aoe || '';
  let save = initialData?.save || '';
  let description = initialData?.description || '';
  let hasReversed = !!initialData?.reversed;
  let reversed = initialData?.reversed || '';

  let submitting = false;
  let error = '';

  async function handleSubmit() {
    if (!name.trim()) { error = 'Spell name is required.'; return; }
    if (!description.trim()) { error = 'Description is required.'; return; }
    submitting = true;
    error = '';

    const payload = {
      name: name.trim(),
      spell_class: spellClass,
      level: parseInt(level),
      description: description.trim(),
      range: range.trim() || null,
      duration: duration.trim() || null,
      aoe: aoe.trim() || null,
      save: save.trim() || null,
      reversed: hasReversed && reversed.trim() ? reversed.trim() : null,
    };

    try {
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
      <label class="block text-sm text-ink mb-1" for="spell-name">Name</label>
      <input id="spell-name" class="input w-full" type="text" bind:value={name} placeholder="Magic Missile" />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-class">Spell Class</label>
        <select id="spell-class" class="input w-full" bind:value={spellClass}>
          {#each SPELL_CLASSES as sc}
            <option value={sc}>{sc}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-level">Level</label>
        <select id="spell-level" class="input w-full" bind:value={level}>
          {#each [1,2,3,4,5,6] as l}
            <option value={l}>{l}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-range">Range</label>
        <input id="spell-range" class="input w-full" type="text" bind:value={range} placeholder="120'" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-duration">Duration</label>
        <input id="spell-duration" class="input w-full" type="text" bind:value={duration} placeholder="1 turn" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-aoe">Area of Effect</label>
        <input id="spell-aoe" class="input w-full" type="text" bind:value={aoe} placeholder="30' radius" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="spell-save">Save</label>
        <input id="spell-save" class="input w-full" type="text" bind:value={save} placeholder="Negates" />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="spell-desc">Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="spell-desc" class="input w-full resize-none" rows="6" bind:value={description} placeholder="Describe the spell's effects..."></textarea>
    </div>

    <div>
      <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
        <input type="checkbox" bind:checked={hasReversed} class="accent-ink" />
        Has Reversed Form
      </label>
      {#if hasReversed}
        <div class="mt-2">
          <label class="block text-sm text-ink mb-1" for="spell-reversed">Reversed Form <span class="text-ink-faint">(supports markdown)</span></label>
          <textarea id="spell-reversed" class="input w-full resize-none" rows="4" bind:value={reversed} placeholder="Describe the reversed version..."></textarea>
        </div>
      {/if}
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Spell'}
    </button>
    <a href="/spells" class="btn-ghost">Cancel</a>
  </div>
</div>
