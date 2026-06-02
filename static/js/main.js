// Sl Presentes — JS leve
document.addEventListener("DOMContentLoaded", () => {
  // Fade-in on cards
  const els = document.querySelectorAll(".card-neo, .stat-card");
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("fade-up");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.1 },
  );
  els.forEach((el) => io.observe(el));

  // Auto-dismiss alerts
  document.querySelectorAll(".alert").forEach((a) => {
    setTimeout(() => {
      a.style.transition = "opacity .4s";
      a.style.opacity = "0";
      setTimeout(() => a.remove(), 400);
    }, 4500);
  });

  // Quantity steppers
  document.querySelectorAll("[data-qty]").forEach((input) => {
    const wrap = input.closest(".qty-stepper");
    if (!wrap) return;
    wrap.querySelector("[data-qty-plus]")?.addEventListener("click", () => {
      input.value = parseInt(input.value || "1") + 1;
    });
    wrap.querySelector("[data-qty-minus]")?.addEventListener("click", () => {
      input.value = Math.max(1, parseInt(input.value || "1") - 1);
    });
  });

  // CEP autocomplete (ViaCEP)
  const cep = document.getElementById("cep");
  if (cep) {
    cep.addEventListener("blur", async () => {
      const v = cep.value.replace(/\D/g, "");
      if (v.length !== 8) return;
      try {
        const r = await fetch(`https://viacep.com.br/ws/${v}/json/`);
        const data = await r.json();
        if (!data.erro) {
          document.getElementById("address").value = data.logradouro || "";
          document.getElementById("city").value = data.localidade || "";
          document.getElementById("state").value = data.uf || "";
        }
      } catch (e) {
        /* offline-friendly */
      }
    });
  }

  const generateBtn = document.getElementById("generate-description-btn");
  const descriptionField = document.getElementById("description");
  const nameField = document.getElementById("name");
  const statusBox = document.getElementById("description-status");

  if (generateBtn && descriptionField && nameField && statusBox) {
    generateBtn.addEventListener("click", async () => {
      const productName = nameField.value.trim();
      const currentDescription = descriptionField.value.trim();

      if (!productName) {
        statusBox.textContent = "Digite o nome do produto antes de gerar a descrição.";
        statusBox.className = "form-text mt-2 text-danger";
        return;
      }

      generateBtn.disabled = true;
      generateBtn.textContent = "⏳ Gerando...";
      statusBox.textContent = "Gerando descrição baseada no nome e em referências de e-commerce...";
      statusBox.className = "form-text mt-2 text-muted";

      try {
        const response = await fetch(
          `/admin/produtos/gerar-descricao?name=${encodeURIComponent(productName)}&description=${encodeURIComponent(currentDescription)}`
        );
        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.message || "Não foi possível gerar a descrição.");
        }

        descriptionField.value = data.description;
        statusBox.textContent =
          data.source === "openai"
            ? "Descrição gerada com IA e pronta para ajustar manualmente."
            : "Descrição padrão gerada. Configure OPENAI_API_KEY para usar a IA com mais contexto.";
        statusBox.className =
          data.source === "openai"
            ? "form-text mt-2 text-success"
            : "form-text mt-2 text-warning";
      } catch (error) {
        statusBox.textContent = error.message || "Erro ao gerar descrição.";
        statusBox.className = "form-text mt-2 text-danger";
      } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "✨ Gerar descrição com IA";
      }
    });
  }
});

// Controle do menu hambúrguer para categorias
document.addEventListener("DOMContentLoaded", function () {
  const categoriesToggle = document.querySelector(".categories-toggle");
  const categoriesList = document.querySelector(".categories-list");
  const dropdowns = document.querySelectorAll(".dropdown-cat");

  // Toggle do menu de categorias
  if (categoriesToggle && categoriesList) {
    categoriesToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      categoriesList.classList.toggle("show");
      categoriesToggle.classList.toggle("active");
    });
  }

  // Fechar menu ao clicar fora (mobile)
  document.addEventListener("click", function (e) {
    if (window.innerWidth <= 768) {
      if (categoriesToggle && categoriesList) {
        if (
          !categoriesToggle.contains(e.target) &&
          !categoriesList.contains(e.target)
        ) {
          categoriesList.classList.remove("show");
          categoriesToggle.classList.remove("active");
        }
      }
    }
  });

  // Controle dos dropdowns no mobile
  if (window.innerWidth <= 768) {
    dropdowns.forEach((dropdown) => {
      const link = dropdown.querySelector("> a");
      if (link) {
        link.addEventListener("click", function (e) {
          e.preventDefault();
          dropdown.classList.toggle("active");
        });
      }
    });
  }

  // Reavaliar dropdowns quando redimensionar
  window.addEventListener("resize", function () {
    if (window.innerWidth > 768) {
      dropdowns.forEach((dropdown) => {
        dropdown.classList.remove("active");
      });
    } else {
      // Recriar eventos se necessário
      dropdowns.forEach((dropdown) => {
        const link = dropdown.querySelector("> a");
        if (link && !link.hasListener) {
          link.addEventListener("click", function (e) {
            e.preventDefault();
            dropdown.classList.toggle("active");
          });
          link.hasListener = true;
        }
      });
    }
  });
});

// 🔥 LIVE SEARCH - Busca em tempo real enquanto digita
document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("searchInput");
  const searchDropdown = document.getElementById("searchDropdown");
  const searchResults = document.getElementById("searchResults");
  const searchForm = document.getElementById("searchForm");

  if (!searchInput) return; // Compatibilidade com páginas sem busca

  let searchTimeout;

  // Função para buscar produtos
  async function performSearch(query) {
    if (!query.trim()) {
      searchDropdown.style.display = "none";
      return;
    }

    try {
      const response = await fetch(
        `/api/search?q=${encodeURIComponent(query)}&limit=8`,
      );
      const data = await response.json();

      // Limpar resultados anteriores
      searchResults.innerHTML = "";

      if (data.results.length === 0) {
        searchDropdown.style.display = "block";
        searchResults.innerHTML =
          '<div class="search-no-results">Nenhum produto encontrado para "' +
          query +
          '"</div>';
        const viewAllBtn = document.createElement("a");
        viewAllBtn.href = "/produtos?q=" + encodeURIComponent(query);
        viewAllBtn.className = "search-view-all";
        viewAllBtn.textContent = "Ver todos os resultados →";
        searchResults.appendChild(viewAllBtn);
        return;
      }

      searchDropdown.style.display = "block";

      // Renderizar cada resultado
      data.results.forEach((product) => {
        const resultItem = document.createElement("a");
        resultItem.href = `/produto/${product.slug}`;
        resultItem.className = "search-result-item";

        const stockStatus =
          product.stock > 0 ? "Em estoque" : "Fora de estoque";
        const stockClass = product.stock > 0 ? "" : "out-of-stock";

        resultItem.innerHTML = `
          <img src="${product.image}" alt="${product.name}" class="search-result-image" onerror="this.src='/static/images/default.png'">
          <div class="search-result-info">
            <div class="search-result-name">${product.name}</div>
            <div class="search-result-details">
              <span class="search-result-price">R$ ${product.price.toFixed(2).replace(".", ",")}</span>
              <span class="search-result-stock ${stockClass}">${stockStatus}</span>
            </div>
          </div>
        `;
        searchResults.appendChild(resultItem);
      });

      // Adicionar botão "Ver todos" se houver resultados
      if (data.results.length > 0) {
        const viewAllBtn = document.createElement("a");
        viewAllBtn.href = "/produtos?q=" + encodeURIComponent(query);
        viewAllBtn.className = "search-view-all";
        viewAllBtn.textContent =
          "Ver todos os resultados (" + data.total + ") →";
        searchResults.appendChild(viewAllBtn);
      }
    } catch (error) {
      console.error("Erro ao buscar produtos:", error);
      searchDropdown.style.display = "none";
    }
  }

  // Evento de digitação na barra de busca
  searchInput.addEventListener("input", function (e) {
    clearTimeout(searchTimeout);
    const query = e.target.value;

    // Aguardar 300ms depois que o usuário deixar de digitar para fazer a requisição
    searchTimeout = setTimeout(() => {
      performSearch(query);
    }, 300);
  });

  // Fechar dropdown quando clicar fora
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search-form-top")) {
      searchDropdown.style.display = "none";
    }
  });

  // Abrir dropdown ao focar no input (se houver valor)
  searchInput.addEventListener("focus", function () {
    if (this.value.trim()) {
      performSearch(this.value);
    }
  });

  // Enviar formulário ao pressionar Enter
  searchForm.addEventListener("submit", function (e) {
    searchDropdown.style.display = "none";
  });
});
