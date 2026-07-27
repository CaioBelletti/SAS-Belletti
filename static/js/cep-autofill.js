// Preenche o endereço automaticamente a partir do CEP, usando o
// ViaCEP (gratuito, sem chave de API). Funciona na ficha de Cliente
// do admin — assim que o CEP tiver 8 dígitos, busca e preenche
// logradouro, bairro, cidade e UF sozinho (só o número e o
// complemento ficam por conta de quem está cadastrando).
(function () {
    function normalizarCep(valor) {
        return (valor || "").replace(/\D/g, "");
    }

    function buscarEndereco(cep) {
        const campoLogradouro = document.getElementById("id_logradouro");
        const campoBairro = document.getElementById("id_bairro");
        const campoCidade = document.getElementById("id_cidade");
        const campoUf = document.getElementById("id_uf");
        if (!campoLogradouro) return; // essa ficha não tem campo de endereço

        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then((resp) => resp.json())
            .then((dados) => {
                if (dados.erro) return; // CEP não encontrado — deixa a pessoa preencher manualmente
                if (campoLogradouro && !campoLogradouro.value) campoLogradouro.value = dados.logradouro || "";
                if (campoBairro && !campoBairro.value) campoBairro.value = dados.bairro || "";
                if (campoCidade && !campoCidade.value) campoCidade.value = dados.localidade || "";
                if (campoUf && !campoUf.value) campoUf.value = dados.uf || "";
            })
            .catch(() => {
                // sem internet ou o serviço fora do ar agora — sem problema,
                // a pessoa só preenche o endereço manualmente como sempre
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        const campoCep = document.getElementById("id_cep");
        if (!campoCep) return;

        campoCep.addEventListener("blur", function () {
            const cep = normalizarCep(campoCep.value);
            if (cep.length === 8) buscarEndereco(cep);
        });

        campoCep.addEventListener("input", function () {
            const cep = normalizarCep(campoCep.value);
            if (cep.length === 8) buscarEndereco(cep);
        });
    });
})();
