/**
 * Shared dungeon tracker state — used by both the full Dungeon Tracker page
 * and the compact widget on the Dungeon Room page.
 *
 * All state is persisted to localStorage per campaign.
 */

import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

const TORCH_LIFE = 6;
const LANTERN_LIFE = 24;
const TURNS_PER_HOUR = 6;

export { TORCH_LIFE, LANTERN_LIFE, TURNS_PER_HOUR };

export function createDungeonTracker(campaignId) {
  const storageKey = `dungeon_tracker_${campaignId}`;

  const state = writable({
    currentTurn: 0,
    torches: [],
    lanterns: [],
    rationsTotal: 0,
    rationsConsumed: 0,
    customTimers: [],
    notes: '',
    history: [],
    nextId: 1,
  });

  function load() {
    if (!browser) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const s = JSON.parse(raw);
      state.set({
        currentTurn: s.currentTurn ?? 0,
        torches: s.torches ?? [],
        lanterns: s.lanterns ?? [],
        rationsTotal: s.rationsTotal ?? 0,
        rationsConsumed: s.rationsConsumed ?? 0,
        customTimers: s.customTimers ?? [],
        notes: s.notes ?? '',
        history: s.history ?? [],
        nextId: s.nextId ?? 1,
      });
    } catch { /* defaults */ }
  }

  function save() {
    if (!browser) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(get(state)));
    } catch { /* storage full */ }
  }

  function advanceTurn(turnNote = '') {
    state.update(s => {
      const currentTurn = s.currentTurn + 1;
      const events = [];

      // Add GM's turn note if provided
      if (turnNote.trim()) {
        events.push({ type: 'note', text: turnNote.trim() });
      }

      // Decrement resources
      let torches = s.torches.map(t => ({ ...t, remaining: t.remaining - 1 }));
      let lanterns = s.lanterns.map(l => ({ ...l, remaining: l.remaining - 1 }));
      let customTimers = s.customTimers.map(t => ({ ...t, remaining: t.remaining - 1 }));

      // Scheduled events
      if (currentTurn % 2 === 0) {
        events.push({ type: 'wandering', text: 'Wandering Monster Check' });
      }
      if (currentTurn % TURNS_PER_HOUR === 0) {
        events.push({ type: 'rest', text: 'Rest Required' });
      }

      // Expired torches
      const expiredTorches = torches.filter(t => t.remaining <= 0);
      if (expiredTorches.length > 0) {
        events.push({ type: 'torch_expired', text: `${expiredTorches.length} torch(es) burned out` });
        torches = torches.filter(t => t.remaining > 0);
      }

      // Expired lanterns
      const expiredLanterns = lanterns.filter(l => l.remaining <= 0 && !l.out);
      if (expiredLanterns.length > 0) {
        events.push({ type: 'lantern_expired', text: `${expiredLanterns.length} lantern(s) out of oil` });
        lanterns = lanterns.map(l => l.remaining <= 0 ? { ...l, out: true } : l);
      }

      // Expired custom timers
      const expiredTimers = customTimers.filter(t => t.remaining <= 0);
      for (const t of expiredTimers) {
        events.push({ type: 'timer_expired', text: `${t.name} expired` });
      }
      customTimers = customTimers.filter(t => t.remaining > 0);

      // Darkness warning
      const activeLights = torches.filter(t => t.remaining > 0).length +
                           lanterns.filter(l => l.remaining > 0).length;
      if (activeLights === 0 && (torches.length > 0 || lanterns.length > 0 || expiredTorches.length > 0 || expiredLanterns.length > 0)) {
        events.push({ type: 'darkness', text: 'No active light sources!' });
      }

      return {
        ...s,
        currentTurn,
        torches,
        lanterns,
        customTimers,
        history: [...s.history, { turn: currentTurn, events: events.map(e => e.text) }],
        _lastEvents: events,
      };
    });
    save();
    return get(state)._lastEvents || [];
  }

  // Derived helpers
  function getStatus() {
    const s = get(state);
    const activeTorches = s.torches.filter(t => t.remaining > 0);
    const activeLanterns = s.lanterns.filter(l => l.remaining > 0);
    return {
      currentTurn: s.currentTurn,
      turnInHour: s.currentTurn > 0 ? ((s.currentTurn - 1) % TURNS_PER_HOUR) + 1 : 0,
      hourNumber: s.currentTurn > 0 ? Math.floor((s.currentTurn - 1) / TURNS_PER_HOUR) + 1 : 0,
      activeTorches: activeTorches.length,
      activeLanterns: activeLanterns.length,
      totalLightSources: activeTorches.length + activeLanterns.length,
      rationsRemaining: s.rationsTotal - s.rationsConsumed,
      // Shortest-lived light source
      nextExpiry: Math.min(
        ...activeTorches.map(t => t.remaining),
        ...activeLanterns.map(l => l.remaining),
        999,
      ),
    };
  }

  // --- Resource management ---

  function addTorch() {
    state.update(s => ({
      ...s,
      torches: [...s.torches, { id: s.nextId, lit_at_turn: s.currentTurn, remaining: TORCH_LIFE }],
      nextId: s.nextId + 1,
    }));
    save();
  }

  function removeTorch(id) {
    state.update(s => ({ ...s, torches: s.torches.filter(t => t.id !== id) }));
    save();
  }

  function addLantern() {
    state.update(s => ({
      ...s,
      lanterns: [...s.lanterns, { id: s.nextId, lit_at_turn: s.currentTurn, remaining: LANTERN_LIFE, out: false }],
      nextId: s.nextId + 1,
    }));
    save();
  }

  function refillLantern(id) {
    state.update(s => ({
      ...s,
      lanterns: s.lanterns.map(l => l.id === id ? { ...l, remaining: LANTERN_LIFE, out: false } : l),
    }));
    save();
  }

  function removeLantern(id) {
    state.update(s => ({ ...s, lanterns: s.lanterns.filter(l => l.id !== id) }));
    save();
  }

  function adjustRations(delta) {
    state.update(s => {
      const total = Math.max(0, s.rationsTotal + delta);
      return { ...s, rationsTotal: total, rationsConsumed: Math.min(s.rationsConsumed, total) };
    });
    save();
  }

  function consumeRation() {
    state.update(s => {
      if (s.rationsConsumed >= s.rationsTotal) return s;
      return { ...s, rationsConsumed: s.rationsConsumed + 1 };
    });
    save();
  }

  function addCustomTimer(name, duration) {
    state.update(s => ({
      ...s,
      customTimers: [...s.customTimers, { id: s.nextId, name, remaining: duration }],
      nextId: s.nextId + 1,
    }));
    save();
  }

  function removeCustomTimer(id) {
    state.update(s => ({ ...s, customTimers: s.customTimers.filter(t => t.id !== id) }));
    save();
  }

  load();

  return {
    state,
    load,
    save,
    advanceTurn,
    getStatus,
    addTorch, removeTorch,
    addLantern, refillLantern, removeLantern,
    adjustRations, consumeRation,
    addCustomTimer, removeCustomTimer,
  };
}
