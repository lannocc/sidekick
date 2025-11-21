<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows } from './windows.js';

    export let isActive;
    export let id;
    export let groupId;

    let display = '0';
    let currentInput = '';
    let previousInput = '';
    let operator = null;

    function clear() {
        display = '0';
        currentInput = '';
        previousInput = '';
        operator = null;
    }

    function backspace() {
        if (display === 'Error') {
            clear();
            return;
        }
        if (currentInput.length > 0) {
            currentInput = currentInput.slice(0, -1);
            display = currentInput === '' ? '0' : currentInput;
        }
    }

    function appendNumber(num) {
        if (currentInput === '0' && num === '0') return;
        if (currentInput === '0' && num !== '0') currentInput = '';
        currentInput += num;
        display = currentInput;
    }

    function appendDecimal() {
        if (currentInput.includes('.')) return;
        if (currentInput === '') currentInput = '0';
        currentInput += '.';
        display = currentInput;
    }

    function chooseOperator(op) {
        if (currentInput === '' && previousInput === '') return;
        if (currentInput !== '') {
            if (previousInput !== '') {
                calculate();
            }
            previousInput = currentInput;
            currentInput = '';
        }
        operator = op;
    }

    function calculate() {
        if (previousInput === '' || currentInput === '' || operator === null) return;
        let result;
        const prev = parseFloat(previousInput);
        const curr = parseFloat(currentInput);

        try {
            // Using a switch is safer than eval()
            switch (operator) {
                case '+': result = prev + curr; break;
                case '-': result = prev - curr; break;
                case '*': result = prev * curr; break;
                case '÷':
                    if (curr === 0) {
                        result = 'Error';
                    } else {
                        result = prev / curr;
                    }
                    break;
                default: return;
            }

            if (result === 'Error') {
                 display = 'Error';
            } else {
                // Limit precision to avoid long floating point numbers
                display = String(parseFloat(result.toPrecision(12)));
            }

            // SENTINEL NOTIFICATION: Trigger for completed calculation
            if (groupId && id) {
                windows.notifyActivity(groupId, id, { summary: `Result: ${display}` });
            }

        } catch (e) {
            display = 'Error';
        }

        currentInput = display !== 'Error' ? display : '';
        previousInput = '';
        operator = null;
    }

    function handleKeydown(e) {
        if (!isActive) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;

        const key = e.key;
        let handled = true;

        switch (key) {
            case '0': case '1': case '2': case '3': case '4':
            case '5': case '6': case '7': case '8': case '9':
                appendNumber(key);
                break;
            case '.':
                appendDecimal();
                break;
            case '+':
                chooseOperator('+');
                break;
            case '-':
                chooseOperator('-');
                break;
            case '*':
                chooseOperator('*');
                break;
            case '/':
                chooseOperator('÷');
                break;
            case 'Enter':
            case '=':
                calculate();
                break;
            case 'Escape':
            case 'Delete':
                clear();
                break;
            case 'Backspace':
                backspace();
                break;
            default:
                handled = false;
                break;
        }

        if (handled) {
            e.preventDefault();
        }
    }

    onMount(() => {
        window.addEventListener('keydown', handleKeydown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', handleKeydown);
    });
</script>

<style>
    .calculator {
        display: flex;
        flex-direction: column;
        height: 100%;
        user-select: none;
    }
    .display {
        background-color: #1a2a3a;
        color: #ecf0f1;
        font-size: 2.5em;
        text-align: right;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 10px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .buttons {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 5px;
        flex-grow: 1;
    }
    .btn {
        font-size: 1.5em;
        border-radius: 4px;
        border: 1px solid var(--border-color);
        background-color: var(--taskbar-button-bg);
        color: var(--taskbar-text);
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .btn:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .btn.operator {
        background-color: #f39c12;
        border-color: #c87f0a;
        color: white;
    }
    .btn.operator:hover {
        background-color: #e67e22;
    }
    .btn.span-2 {
        grid-column: span 2;
    }
    .btn.clear {
        background-color: #e74c3c;
        border-color: #c0392b;
        color: white;
    }
     .btn.clear:hover {
        background-color: #c0392b;
    }
</style>

<div class="calculator">
    <div class="display">{display}</div>
    <div class="buttons">
        <button class="btn clear span-2" on:click={clear}>C</button>
        <button class="btn operator" on:click={() => chooseOperator('÷')}>÷</button>
        <button class="btn operator" on:click={() => chooseOperator('*')}>*</button>

        <button class="btn" on:click={() => appendNumber('7')}>7</button>
        <button class="btn" on:click={() => appendNumber('8')}>8</button>
        <button class="btn" on:click={() => appendNumber('9')}>9</button>
        <button class="btn operator" on:click={() => chooseOperator('-')}>-</button>

        <button class="btn" on:click={() => appendNumber('4')}>4</button>
        <button class="btn" on:click={() => appendNumber('5')}>5</button>
        <button class="btn" on:click={() => appendNumber('6')}>6</button>
        <button class="btn operator" on:click={() => chooseOperator('+')}>+</button>

        <button class="btn" on:click={() => appendNumber('1')}>1</button>
        <button class="btn" on:click={() => appendNumber('2')}>2</button>
        <button class="btn" on:click={() => appendNumber('3')}>3</button>
        <button class="btn" on:click={calculate} style="grid-row: span 2;">=</button>

        <button class="btn span-2" on:click={() => appendNumber('0')}>0</button>
        <button class="btn" on:click={appendDecimal}>.</button>
    </div>
</div>