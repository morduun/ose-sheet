<script>
  import { api } from '$lib/api.js';

  export let character;

  let notes = character.notes ?? '';
  let saving = false;
  let savedMsg = '';

  async function saveNotes() {
    if (notes === (character.notes ?? '')) return;
    saving = true;
    try {
      await api.patch(`/characters/${character.id}`, { notes });
      character = { ...character, notes };
      savedMsg = 'Saved';
      setTimeout(() => (savedMsg = ''), 2000);
    } catch (e) {
      alert(e.message);
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-6">
  <div class="panel">
    <div class="flex items-center justify-between mb-3">
      <h2 class="section-title mb-0 border-none">Notes</h2>
      <span class="text-xs text-ink-faint">{savedMsg}</span>
    </div>
    <textarea
      class="input w-full resize-y min-h-[200px] font-sans text-sm"
      placeholder="Character notes, backstory, quest hooks…"
      bind:value={notes}
      on:blur={saveNotes}
    ></textarea>
    <p class="text-xs text-ink-faint mt-1">Auto-saves on blur.</p>
  </div>
</div>
