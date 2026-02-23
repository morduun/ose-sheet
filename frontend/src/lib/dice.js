import DiceBox from '@3d-dice/dice-box';

let diceBox = null;
let clearTimer = null;

export async function initDice(containerSelector) {
  // If the previous DiceBox's container was removed from the DOM
  // (e.g. SvelteKit navigation), we must re-initialize.
  if (diceBox) {
    const el = document.querySelector(containerSelector);
    if (el && el.querySelector('canvas')) {
      return; // existing instance is still attached — reuse it
    }
    // Container is gone or empty — tear down stale instance
    destroyDice();
  }

  diceBox = new DiceBox(containerSelector, {
    assetPath: '/assets/dice-box/',
    themeColor: '#2c1810',
    scale: 8,
    gravity: 1,
    enableShadows: false,
  });

  await diceBox.init();
}

export function destroyDice() {
  if (clearTimer) {
    clearTimeout(clearTimer);
    clearTimer = null;
  }
  if (diceBox) {
    try { diceBox.clear(); } catch { /* already gone */ }
  }
  diceBox = null;
}

export async function rollDice(notation) {
  if (!diceBox) throw new Error('Dice not initialized');

  if (clearTimer) {
    clearTimeout(clearTimer);
    clearTimer = null;
  }

  const results = await diceBox.roll(notation);

  // Sum up all group values
  const total = results.reduce((sum, group) => sum + group.value, 0);

  // Auto-clear dice from canvas after 1.5s
  clearTimer = setTimeout(() => {
    diceBox.clear();
    clearTimer = null;
  }, 1500);

  return total;
}
