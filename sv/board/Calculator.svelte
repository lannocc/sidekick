<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows } from '../windows.js';

    export let isActive;
    export let id;
    export let groupId;

    // --- State Management ---
    // These props are used for initialization when the component is created/restored.
    export let display = '0';
    export let currentInput = '';
    export let previousInput = '';
    export let operator = null;
    export let lastOperand = '';
    export let lastOperator = null;
    export let calculationDone = false;

    // Local state variables that hold the actual, live state of the calculator.
    // They are initialized from the props once.
    let localDisplay, localCurrentInput, localPreviousInput, localOperator, localLastOperand, localLastOperator, localCalculationDone;

    // This reactive block synchronizes the component's internal state with its
    // props. This is crucial for when the component instance is preserved (e.g.,
    // during a back/unback transition) and its state needs to be restored from
    // the new props. It runs initially and whenever the props change.
    $: {
        localDisplay = display;
        localCurrentInput = currentInput;
        localPreviousInput = previousInput;
        localOperator = operator;
        localLastOperand = lastOperand;
        localLastOperator = lastOperator;
        localCalculationDone = calculationDone;
    }

    // This function is called by the window manager to save the component's state.
    // It now returns the local state, not the initial props.
    export function getState() {
        return {
            display: localDisplay,
            currentInput: localCurrentInput,
            previousInput: localPreviousInput,
            operator: localOperator,
            lastOperand: localLastOperand,
            lastOperator: localLastOperator,
            calculationDone: localCalculationDone,
        };
    }
    // --- End State Management ---

    let calculatorEl;

    function clear() {
        localDisplay = '0';
        localCurrentInput = '';
        localPreviousInput = '';
        localOperator = null;
        localLastOperand = '';
        localLastOperator = null;
        localCalculationDone = false;
    }

    function backspace() {
        if (localDisplay === 'Error') {
            clear();
            return;
        }
        if (localCurrentInput.length > 0) {
            localCurrentInput = localCurrentInput.slice(0, -1);
            localDisplay = localCurrentInput === '' ? '0' : localCurrentInput;
        }
    }

    function appendNumber(num) {
        if (localCalculationDone) {
            localCurrentInput = '';
            localCalculationDone = false;
        }
        if (localCurrentInput === '0' && num === '0') return;
        if (localCurrentInput === '0' && num !== '0') localCurrentInput = '';
        localCurrentInput += num;
        localDisplay = localCurrentInput;
    }

    function appendDecimal() {
        if (localCalculationDone) {
            localCurrentInput = '';
            localCalculationDone = false;
        }
        if (localCurrentInput.includes('.')) return;
        if (localCurrentInput === '') localCurrentInput = '0';
        localCurrentInput += '.';
        localDisplay = localCurrentInput;
    }

    function chooseOperator(op) {
        localCalculationDone = false;
        if (localCurrentInput === '' && localPreviousInput === '') return;
        if (localCurrentInput !== '') {
            if (localPreviousInput !== '') {
                calculate();
            }
            localPreviousInput = localDisplay; // Use display in case it's a result
            localCurrentInput = '';
        }
        localOperator = op;
    }

    function calculate() {
        let result;
        let prev, curr, op;
        let calculationString;

        if (localOperator) { // Normal calculation
            if (localPreviousInput === '') return;
            // Handle "5 * =" case
            if (localCurrentInput === '') {
                localCurrentInput = localPreviousInput;
            }
            prev = parseFloat(localPreviousInput);
            curr = parseFloat(localCurrentInput);
            op = localOperator;
            calculationString = `${localPreviousInput} ${op} ${localCurrentInput}`;

            localLastOperand = localCurrentInput;
            localLastOperator = op;

        } else if (localLastOperator) { // Repeated calculation
            if (localCurrentInput === '' || localLastOperand === '') return;
            prev = parseFloat(localCurrentInput);
            curr = parseFloat(localLastOperand);
            op = localLastOperator;
            calculationString = `${localCurrentInput} ${op} ${localLastOperand}`;
            localPreviousInput = localCurrentInput; 
        } else {
            return; // Nothing to do
        }

        try {
            switch (op) {
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
                 localDisplay = 'Error';
            } else {
                localDisplay = String(parseFloat(result.toPrecision(12)));
            }

            if (groupId && id && calculationString) {
                windows.notifyActivity(groupId, id, { summary: `${calculationString} = ${localDisplay}` }, true);
            }

        } catch (e) {
            localDisplay = 'Error';
        }

        localCurrentInput = localDisplay !== 'Error' ? localDisplay : '';
        localPreviousInput = '';
        localOperator = null;
        localCalculationDone = true;
    }

    function handleKeydown(e) {
        if (!isActive) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;

        const key = e.key;
        let handled = true;
        let buttonKey;

        switch (key) {
            case '0': case '1': case '2': case '3': case '4':
            case '5': case '6': case '7': case '8': case '9':
                appendNumber(key);
                buttonKey = key;
                break;
            case '.':
                appendDecimal();
                buttonKey = '.';
                break;
            case '+':
                chooseOperator('+');
                buttonKey = '+';
                break;
            case '-':
                chooseOperator('-');
                buttonKey = '-';
                break;
            case '*':
                chooseOperator('*');
                buttonKey = '*';
                break;
            case '/':
                chooseOperator('÷');
                buttonKey = '÷';
                break;
            case 'Enter':
            case '=':
                calculate();
                buttonKey = '=';
                break;
            case 'Escape':
            case 'Delete':
                clear();
                buttonKey = 'C';
                break;
            case 'Backspace':
                backspace();
                buttonKey = 'Backspace';
                break;
            default:
                handled = false;
                break;
        }

        if (handled) {
            e.preventDefault();
            if (buttonKey && calculatorEl) {
                const button = calculatorEl.querySelector(`.btn[data-key="${buttonKey}"]`);
                if (button) {
                    button.classList.add('active');
                    setTimeout(() => {
                        button.classList.remove('active');
                    }, 150);
                }
            }
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
        transition: background-color 0.2s, transform 0.05s ease-in-out, filter 0.05s ease-in-out;
    }
    .btn:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .btn:active, .btn.active {
        transform: scale(0.95);
        filter: brightness(1.2);
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

<div class="calculator" bind:this={calculatorEl}>
    <div class="display">{localDisplay}</div>
    <div class="buttons">
        <button class="btn clear" on:click={clear} data-key="C">C</button>
        <button class="btn" on:click={backspace} data-key="Backspace">⌫</button>
        <button class="btn operator" on:click={() => chooseOperator('÷')} data-key="÷">÷</button>
        <button class="btn operator" on:click={() => chooseOperator('*')} data-key="*">*</button>

        <button class="btn" on:click={() => appendNumber('7')} data-key="7">7</button>
        <button class="btn" on:click={() => appendNumber('8')} data-key="8">8</button>
        <button class="btn" on:click={() => appendNumber('9')} data-key="9">9</button>
        <button class="btn operator" on:click={() => chooseOperator('-')} data-key="-">-</button>

        <button class="btn" on:click={() => appendNumber('4')} data-key="4">4</button>
        <button class="btn" on:click={() => appendNumber('5')} data-key="5">5</button>
        <button class="btn" on:click={() => appendNumber('6')} data-key="6">6</button>
        <button class="btn operator" on:click={() => chooseOperator('+')} data-key="+">+</button>

        <button class="btn" on:click={() => appendNumber('1')} data-key="1">1</button>
        <button class="btn" on:click={() => appendNumber('2')} data-key="2">2</button>
        <button class="btn" on:click={() => appendNumber('3')} data-key="3">3</button>
        <button class="btn" on:click={calculate} style="grid-row: span 2;" data-key="=">=</button>

        <button class="btn span-2" on:click={() => appendNumber('0')} data-key="0">0</button>
        <button class="btn" on:click={appendDecimal} data-key=".">.</button>
    </div>
</div>
