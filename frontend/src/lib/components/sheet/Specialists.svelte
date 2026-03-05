<script>
  import { api } from '$lib/api.js';

  export let character;
  export let isGM = false;
  export let isOwner = false;

  let specTypes = null;
  let loading = false;
  let showHireForm = false;
  let saving = false;
  let removingId = null;
  let paying = false;

  // Hire form state
  let hireType = '';
  let hireTask = '';

  $: specs = character?.specialists ?? [];
  $: totalCost = specs.reduce((s, e) => s + e.wage, 0);
  $: canEdit = isOwner || isGM;

  // Wage preview for selected type
  $: hireWagePreview = (() => {
    if (!specTypes || !hireType) return null;
    const t = specTypes.find(t => t.key === hireType);
    return t ? t.wage : null;
  })();

  async function ensureTypes() {
    if (specTypes) return;
    loading = true;
    try {
      specTypes = await api.get('/specialist-types');
    } catch (e) {
      alert('Failed to load specialist types');
    } finally {
      loading = false;
    }
  }

  function openHireForm() {
    ensureTypes();
    showHireForm = true;
    hireType = '';
    hireTask = '';
  }

  async function hire() {
    if (!hireType) return;
    saving = true;
    try {
      const entry = await api.post(`/characters/${character.id}/specialists`, {
        spec_type: hireType,
        task: hireTask || null,
      });
      character.specialists = [...specs, entry];
      character = character;
      showHireForm = false;
    } catch (e) {
      alert(e.message || 'Failed to hire specialist');
    } finally {
      saving = false;
    }
  }

  async function updateTask(spec, newTask) {
    const trimmed = newTask.trim() || null;
    if (trimmed === (spec.task || null)) return;
    try {
      const updated = await api.patch(`/characters/${character.id}/specialists/${spec.id}`, {
        task: trimmed,
      });
      const idx = specs.findIndex(s => s.id === spec.id);
      if (idx >= 0) specs[idx] = updated;
      character.specialists = [...specs];
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to update task');
    }
  }

  async function dismiss(spec) {
    if (!confirm(`Dismiss ${spec.name}?`)) return;
    removingId = spec.id;
    try {
      await api.delete(`/characters/${character.id}/specialists/${spec.id}`);
      character.specialists = specs.filter(s => s.id !== spec.id);
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to dismiss');
    } finally {
      removingId = null;
    }
  }

  async function payday() {
    if (!confirm(`Pay ${totalCost} gp for one month's specialist wages?`)) return;
    paying = true;
    try {
      const result = await api.post(`/characters/${character.id}/specialists/payday`);
      character.platinum = result.platinum;
      character.gold = result.gold;
      character.electrum = result.electrum;
      character.silver = result.silver;
      character.copper = result.copper;
      character = character;
      alert(`Paid ${result.cost_gp} gp in specialist wages.`);
    } catch (e) {
      alert(e.message || 'Failed to pay specialists');
    } finally {
      paying = false;
    }
  }
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
    <h2 class="section-title">
      Specialists ({specs.length} hired | {totalCost} gp/mo)
    </h2>
    <div class="flex items-center gap-3">
      {#if specs.length > 0 && canEdit}
        <button
          class="btn text-sm"
          disabled={paying || totalCost === 0}
          on:click={payday}
          title="Deduct {totalCost} gp from character wealth"
        >
          {paying ? 'Paying...' : 'Payday'}
        </button>
      {/if}
      {#if canEdit}
        <button class="btn text-sm" on:click={openHireForm}>
          + Hire
        </button>
      {/if}
    </div>
  </div>

  <!-- Hire Form -->
  {#if showHireForm}
    <div class="panel mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-medium text-sm">Hire Specialist</h3>
        <button class="btn-ghost text-xs" on:click={() => (showHireForm = false)}>Cancel</button>
      </div>
      {#if loading}
        <p class="text-ink-faint text-sm">Loading types...</p>
      {:else if specTypes}
        <div class="grid gap-3 sm:grid-cols-3">
          <!-- Type -->
          <div>
            <label class="text-xs text-ink-faint block mb-1">Type</label>
            <select bind:value={hireType} class="input text-sm w-full">
              <option value="">Select...</option>
              {#each specTypes as t}
                <option value={t.key}>{t.name} ({t.wage} gp/mo)</option>
              {/each}
            </select>
          </div>
          <!-- Task -->
          <div>
            <label class="text-xs text-ink-faint block mb-1">Task (optional)</label>
            <input
              type="text"
              bind:value={hireTask}
              placeholder="What are they doing?"
              class="input text-sm w-full"
              maxlength="500"
            />
          </div>
          <!-- Hire button -->
          <div class="flex items-end">
            <button
              class="btn text-sm w-full"
              disabled={!hireType || saving}
              on:click={hire}
            >
              {#if hireWagePreview != null}
                Hire ({hireWagePreview} gp/mo)
              {:else}
                Hire
              {/if}
            </button>
          </div>
        </div>
        <!-- Type description -->
        {#if hireType}
          {@const info = specTypes.find(t => t.key === hireType)}
          {#if info}
            <p class="text-xs text-ink-faint mt-2">{info.desc}</p>
          {/if}
        {/if}
      {/if}
    </div>
  {/if}

  <!-- Specialists Table -->
  {#if specs.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">
        No specialists hired. They perform non-combat services for a monthly wage.
      </p>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b border-ink-faint/30 text-left text-xs text-ink-faint">
            <th class="py-1.5 pr-2">Type</th>
            <th class="py-1.5 pr-2 text-right">Wage</th>
            <th class="py-1.5 pr-2">Task</th>
            {#if canEdit}
              <th class="py-1.5 text-right">Actions</th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each specs as spec (spec.id)}
            <tr class="border-b border-ink-faint/10 hover:bg-parchment-200/50">
              <td class="py-1.5 pr-2">
                <span class="font-medium">{spec.name}</span>
              </td>
              <td class="py-1.5 pr-2 text-right">{spec.wage} gp</td>
              <td class="py-1.5 pr-2">
                {#if canEdit}
                  <input
                    type="text"
                    class="input text-sm w-full bg-transparent border-ink-faint/20"
                    value={spec.task ?? ''}
                    placeholder="Idle"
                    maxlength="500"
                    on:blur={(e) => updateTask(spec, e.target.value)}
                    on:keydown={(e) => { if (e.key === 'Enter') e.target.blur(); }}
                  />
                {:else}
                  <span class="text-ink-faint">{spec.task || 'Idle'}</span>
                {/if}
              </td>
              {#if canEdit}
                <td class="py-1.5 text-right whitespace-nowrap">
                  <button
                    class="btn-ghost text-xs text-red-700 hover:text-red-900 px-1"
                    disabled={removingId === spec.id}
                    on:click={() => dismiss(spec)}
                    title="Dismiss specialist"
                  >{removingId === spec.id ? '...' : 'x'}</button>
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
