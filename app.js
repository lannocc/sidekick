/*
 * Copyright (C) 2025 LANNOCC
 * @%@~LICENSE~@%@
 */

import { mount } from 'svelte';
import SideKick from './sv/SideKick.svelte';

const app = mount(SideKick, {
    target: document.body,
});

export default app;

