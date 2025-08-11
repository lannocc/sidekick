<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->

<script>
  /*
  import { onMount, tick } from 'svelte';

  //import Home from './Home.svelte';

  let sws = '...';
  let sws_class = '';
  let ver;

  let comp = Home;
  let activated = false;
  let config = false;

  const main_menu = {
      'Home': [ Home ],
  };

  onMount(async () => {
    sk_on_message(on_sk, 1);

    //FIXME: a better way for this...
    if ('' === new URLSearchParams(document.location.search).get('kick')) {
      main_reset();
      document.location.search = '';
    }
    else {
      //if (!$policies || !$users) await refresh();
    }

    const status = sk_status();
    sws = status[0];
    sws_class = status[1];
  });

  async function on_sk(msg) {
    if ('Version' in msg) {
      ver = msg.Version.code;
      // let pass-through for Admin/Status screen:
      //return true;
      return false;
    }
  }

  async function refresh() {
    await sk_call('GetVersion');
  }
  */
</script>

HELLO WORLD

<!--

<header>
  <h1>
    <a href="?kick" title="SideKick AI">
    <!- -a on:click={async () => main_reset()} title="SideKick AI"- ->
      <img id="status_img"
           src="/img/logo.png"
           alt="SideKick"
           class={sws_class}>
    </a>
    <span id="mod_title">
      SideKick AI
    </span>
  </h1>

  <aside>
    <div id="user" class="hover_menu">
      <img src="/img/user.png">
      <menu>
        <li>Profile</li>
        <li>Settings</li>
      </menu>
    </div>
  </aside>
</header>

<main>
  <nav id="main_menu" class:activated>
    <img id="hamburger" src="/img/hamburger.png" title="Show/hide menu"
         on:click={() => (activated = !activated)}>

    <menu>
      {#each Object.entries(main_menu) as [ name, data ]}

        <li class:current={$main_mod == name}>
          <a on:click={() => main_set(name)} title={name}>
            <img src="/img/{data[1]}">
            <span class="label">{name}</span>
          </a>

          {#if data[2]}
            <menu class="mod_menu">
              {#each Object.entries(data[2]) as [ name2, comp ]}
                {#if name2 == 'Home'}
                {:else if name2 == '---'}
                  <hr>
                {:else}
                  <li><a on:click={() => main_set(name, name2)}
                         class:current={$main == name+'.'+name2}
                         href="#">{name2}</a></li>
                {/if}
              {/each}
            </menu>
          {/if}
        </li>
      {/each}
    </menu>
  </nav>

  <section>
    <svelte:component this={comp}/>
  </section>
</main>

<footer>
  {#if ver}<sub title="Version {ver}">{ver}</sub>{/if}
  <span title="All Rights Reserved.">&copy;</span>
  <sup title="Copyright (C) LANNOCC">2025</sup>
</footer>
-->
