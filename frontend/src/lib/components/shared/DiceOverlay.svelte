<script>
  import { onMount, onDestroy } from 'svelte';
  import { initDice, rollDice, destroyDice } from '$lib/dice.js';

  export let roll = null;

  let toastVisible = false;
  let toastTotal = null;
  let toastNotation = '';
  let toastInterpretation = '';
  let dismissTimer = null;
  let rolling = false;

  onMount(async () => {
    try {
      await initDice('#dice-overlay');
    } catch (e) {
      console.warn('Dice init failed:', e);
    }
  });

  onDestroy(() => {
    destroyDice();
  });

  function dismissToast() {
    toastVisible = false;
    if (dismissTimer) {
      clearTimeout(dismissTimer);
      dismissTimer = null;
    }
  }

  async function doRoll(notation, interpretFn) {
    if (rolling) return;
    rolling = true;
    dismissToast();

    try {
      const total = await rollDice(notation);
      toastTotal = total;
      toastNotation = notation;
      toastInterpretation = interpretFn ? interpretFn(total) : '';
      toastVisible = true;

      dismissTimer = setTimeout(dismissToast, 4000);
      return total;
    } catch (e) {
      console.error('Roll failed:', e);
    } finally {
      rolling = false;
    }
  }

  // Bind the roll function so the parent can call it
  $: roll = doRoll;
</script>

<!-- Dice canvas container — transparent, pointer-events: none so it doesn't block UI -->
<div
  id="dice-overlay"
  class="fixed inset-0 z-40 pointer-events-none print:hidden"
  style="width: 100vw; height: 100vh;"
></div>

<!-- Result toast -->
{#if toastVisible}
  <button
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 panel shadow-lg
           cursor-pointer print:hidden min-w-[200px] text-center
           animate-slide-up"
    on:click={dismissToast}
  >
    <div class="font-serif text-3xl text-ink">{toastTotal}</div>
    <div class="text-sm text-ink-faint">
      {toastNotation}{#if toastInterpretation} &rarr; {toastInterpretation}{/if}
    </div>
  </button>
{/if}

<style>
  /* DiceBox creates a <canvas> inside #dice-overlay — it must fill the container */
  #dice-overlay :global(canvas) {
    width: 100% !important;
    height: 100% !important;
  }

  .animate-slide-up {
    animation: slideUp 0.25s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(16px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
</style>
