<script>
  import { createEventDispatcher } from 'svelte';
  import { HEX_W, HEX_H, HEX_POINTS, hexX, hexY, gridViewBox, terrainIcon } from '$lib/hex-terrain.js';

  export let width = 10;
  export let height = 8;
  export let cells = [];
  export let partyCol = null;
  export let partyRow = null;
  export let selectedCol = null;
  export let selectedRow = null;
  export let fogOfWar = false;
  export let zoom = 1;

  const dispatch = createEventDispatcher();

  $: vb = gridViewBox(width, height);

  // Merge cell data into grid positions — reactive on cells, width, height
  $: gridData = (() => {
    const lookup = new Map(cells.map(c => [`${c.col},${c.row}`, c]));
    const data = [];
    for (let col = 0; col < width; col++) {
      for (let row = 0; row < height; row++) {
        data.push({
          col, row,
          x: hexX(col),
          y: hexY(col, row),
          cell: lookup.get(`${col},${row}`) || null,
        });
      }
    }
    return data;
  })();

  function handleClick(col, row, cell) {
    dispatch('cellclick', { col, row, cell });
  }
</script>

<div class="hex-grid-container" style="overflow: auto; max-height: 70vh;">
  <svg
    viewBox="0 0 {vb.w} {vb.h}"
    width={vb.w * zoom}
    height={vb.h * zoom}
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    class="hex-grid"
  >
    <defs>
      <clipPath id="hex-clip">
        <polygon points={HEX_POINTS} />
      </clipPath>
    </defs>

    {#each gridData as hex (`${hex.col},${hex.row}`)}
      {@const fogged = fogOfWar && !hex.cell?.visited}

      <g
        transform="translate({hex.x}, {hex.y})"
        on:click={() => handleClick(hex.col, hex.row, hex.cell)}
        on:keydown={(e) => e.key === 'Enter' && handleClick(hex.col, hex.row, hex.cell)}
        role="button"
        tabindex="0"
        class="hex-cell"
        style="cursor: pointer;"
      >
        {#if hex.cell && !fogged}
          <!-- Terrain icon -->
          <image
            href={terrainIcon(hex.cell.terrain_type)}
            width={HEX_W}
            height={HEX_H}
            clip-path="url(#hex-clip)"
          />
        {:else if fogged && hex.cell}
          <!-- Fogged cell — dark overlay -->
          <polygon points={HEX_POINTS} fill="#3a3226" fill-opacity="0.85" />
          <polygon points={HEX_POINTS} fill="none" stroke="#5a4e3e" stroke-width="0.5" />
        {:else}
          <!-- Empty cell — dashed outline -->
          <polygon
            points={HEX_POINTS}
            fill="#f5f0e8"
            fill-opacity="0.15"
            stroke="#9e8e76"
            stroke-width="0.5"
            stroke-dasharray="4,3"
          />
        {/if}

        <!-- Cell border (on top of terrain) -->
        {#if hex.cell && !fogged}
          <polygon points={HEX_POINTS} fill="none" stroke="#5a4e3e" stroke-width="0.5" />
        {/if}

        <!-- Selection highlight -->
        {#if selectedCol === hex.col && selectedRow === hex.row}
          <polygon points={HEX_POINTS} fill="none" stroke="#c59a3b" stroke-width="3" />
        {/if}

        <!-- Visited indicator (small dot) -->
        {#if hex.cell?.visited && !fogOfWar}
          <circle cx="38" cy="58" r="3" fill="#4a7c59" fill-opacity="0.7" />
        {/if}

        <!-- POI indicator -->
        {#if hex.cell?.pois?.length > 0 && !fogged}
          <circle cx="38" cy="8" r="5" fill="#8b4513" stroke="#fff" stroke-width="1" />
          <text x="38" y="11" text-anchor="middle" fill="#fff" font-size="7" font-weight="bold">!</text>
        {/if}

        <!-- Cell name label -->
        {#if hex.cell?.name && !fogged}
          <text
            x="38" y="40"
            text-anchor="middle"
            fill="#1a1408"
            font-size="8"
            font-family="serif"
            paint-order="stroke"
            stroke="#f5f0e8"
            stroke-width="2"
          >{hex.cell.name}</text>
        {/if}
      </g>
    {/each}

    <!-- Party marker (rendered last, on top of everything) -->
    {#if partyCol != null && partyRow != null}
      {@const px = hexX(partyCol) + HEX_W / 2}
      {@const py = hexY(partyCol, partyRow) + HEX_H / 2}
      <g transform="translate({px}, {py})">
        <!-- Flag pole -->
        <line x1="0" y1="4" x2="0" y2="-14" stroke="#1a1408" stroke-width="2" />
        <!-- Flag -->
        <polygon points="1,-14 12,-10 1,-6" fill="#b91c1c" stroke="#1a1408" stroke-width="0.5" />
        <!-- Base -->
        <circle cx="0" cy="4" r="4" fill="#b91c1c" stroke="#fff" stroke-width="1.5" />
      </g>
    {/if}
  </svg>
</div>

<style>
  .hex-grid-container {
    border: 1px solid #d4c9b0;
    border-radius: 0.375rem;
    background: #2a2418;
  }
  .hex-cell:hover polygon {
    filter: brightness(1.1);
  }
  .hex-cell:focus {
    outline: none;
  }
</style>
