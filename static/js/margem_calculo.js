// Calcula o preço de venda sugerido em tempo real, no admin de Produto,
// a partir do preço de custo + margem desejada (%).
document.addEventListener('DOMContentLoaded', function () {
    const custoInput = document.getElementById('id_preco_custo');
    const margemInput = document.getElementById('id_margem_desejada');
    const vendaInput = document.getElementById('id_preco_venda');

    if (!custoInput || !margemInput || !vendaInput) return;

    function recalcular() {
        const custo = parseFloat(custoInput.value);
        const margem = parseFloat(margemInput.value);
        if (!isNaN(custo) && !isNaN(margem) && margem > 0 && custo >= 0) {
            const sugerido = custo * (1 + margem / 100);
            vendaInput.value = sugerido.toFixed(2);
        }
    }

    custoInput.addEventListener('input', recalcular);
    margemInput.addEventListener('input', recalcular);
});
