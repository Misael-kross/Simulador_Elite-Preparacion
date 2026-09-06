let ultimaCategoria = "biblioteca";
let categoriaActual = "";
let materiaActualSeleccionada = "";
let areaUniversidadActual = "";
let origenMateriasSimulador = "simuladores";

let examenActual = null;
let preguntas = [];
let preguntaActual = 0;
let respuestasUsuario = {};
let contadorIntervalo = null;
let tiempoRestanteSegundos = 0;
let contadorActivado = false;
let respuestasOcultasActivadas = true;
let respuestaVisible = null;
let configuracionEsPorMateria = false;

const rutasBase = {
  ECOEMS: "preguntas/ecoems/",
  "CENEVAL EXANI I": "preguntas/ceneval_exani_i/",
  "UACH Bachillerato": "preguntas/uach_bachillerato/"
};

const areasUniversidad = {
  UNAM: [
    { id: "area1", titulo: "Área 1", descripcion: "Ciencias Físico-Matemáticas y de las Ingenierías" },
    { id: "area2", titulo: "Área 2", descripcion: "Ciencias Biológicas, Químicas y de la Salud" },
    { id: "area3", titulo: "Área 3", descripcion: "Ciencias Sociales" },
    { id: "area4", titulo: "Área 4", descripcion: "Humanidades y Artes" }
  ],
  IPN: [
    { id: "iycfm", titulo: "IyCFM", descripcion: "Ingeniería y Ciencias Físico-Matemáticas" },
    { id: "cmb", titulo: "CMB", descripcion: "Ciencias Médico-Biológicas" },
    { id: "csa", titulo: "CSA", descripcion: "Ciencias Sociales y Administrativas" }
  ],
  UAM: [
    { id: "cbi", titulo: "CBI", descripcion: "Ciencias Básicas e Ingeniería" },
    { id: "cbs", titulo: "CBS", descripcion: "Ciencias Biológicas y de la Salud" },
    { id: "csh", titulo: "CSH", descripcion: "Ciencias Sociales y Humanidades" },
    { id: "cad", titulo: "CAD", descripcion: "Ciencias y Artes para el Diseño" },
    { id: "cni", titulo: "CNI", descripcion: "Ciencias Naturales e Ingeniería - Unidad Cuajimalpa" },
    { id: "ccd", titulo: "CCD", descripcion: "Ciencias de la Comunicación y Diseño - Unidad Cuajimalpa" }
  ],
  "EXANI II": [
    { id: "premedicina", titulo: "Premedicina", descripcion: "Módulo específico" },
    { id: "ciencias_salud", titulo: "Ciencias de la Salud", descripcion: "Módulo específico" },
    { id: "calculo_diferencial_integral", titulo: "Cálculo diferencial e integral", descripcion: "Módulo específico" },
    { id: "fisica", titulo: "Física", descripcion: "Módulo específico" },
    { id: "quimica", titulo: "Química", descripcion: "Módulo específico" },
    { id: "biologia", titulo: "Biología", descripcion: "Módulo específico" },
    { id: "administracion", titulo: "Administración", descripcion: "Módulo específico" },
    { id: "economia", titulo: "Economía", descripcion: "Módulo específico" },
    { id: "derecho", titulo: "Derecho", descripcion: "Módulo específico" },
    { id: "ciencias_sociales", titulo: "Ciencias Sociales", descripcion: "Módulo específico" },
    { id: "historia", titulo: "Historia", descripcion: "Módulo específico" },
    { id: "literatura", titulo: "Literatura", descripcion: "Módulo específico" },
    { id: "filosofia", titulo: "Filosofía", descripcion: "Módulo específico" },
    { id: "psicologia", titulo: "Psicología", descripcion: "Módulo específico" },
    { id: "probabilidad_estadistica", titulo: "Probabilidad y Estadística", descripcion: "Módulo específico" },
    { id: "aritmetica_matematicas_financieras", titulo: "Aritmética / Matemáticas Financieras", descripcion: "Módulo específico" }
  ],
  "UACH Universidad": [
    { id: "medicina_ciencias_biomedicas", titulo: "Medicina y Ciencias Biomédicas", descripcion: "Premedicina" },
    { id: "ingenieria", titulo: "Ingeniería", descripcion: "Cálculo diferencial e integral + Física" },
    { id: "derecho", titulo: "Derecho", descripcion: "Derecho + Ciencias Sociales / Historia" },
    { id: "contaduria_administracion", titulo: "Contaduría y Administración", descripcion: "Administración + Aritmética / Matemáticas Financieras" }
  ]
};

const clavesUniversidad = {
  UNAM: "unam",
  IPN: "ipn",
  UAM: "uam",
  "EXANI II": "exani_ii",
  "UACH Universidad": "uach"
};

const materiasPorCategoria = {
  ECOEMS: [
    "Habilidad Verbal",
    "Habilidad Matemática",
    "Matemáticas",
    "Física",
    "Química",
    "Biología",
    "Español",
    "Historia de México",
    "Historia Universal",
    "Geografía",
    "Formación Cívica y Ética"
  ],

  "CENEVAL EXANI I": [
    "Pensamiento científico",
    "Comprensión lectora",
    "Redacción indirecta",
    "Pensamiento matemático"
  ],

  "UACH Bachillerato": [
    "Habilidades numéricas",
    "Habilidades verbales",
    "Matemáticas",
    "Física",
    "Química",
    "Biología",
    "Geografía",
    "Lengua y Literatura",
    "Historia mundial",
    "Historia de México"
  ],

  UNAM: [
    "Español",
    "Física",
    "Matemáticas",
    "Literatura",
    "Geografía",
    "Biología",
    "Química",
    "Historia Universal",
    "Historia de México"
  ],

  IPN: [
    "Matemáticas",
    "Competencia escrita",
    "Competencia lectora",
    "Inglés",
    "Historia",
    "Biología",
    "Química",
    "Física"
  ],

  UAM: [
    "Razonamiento verbal",
    "Comprensión lectora",
    "Comunicación escrita",
    "Razonamiento matemático",
    "Ciencias Básicas e Ingeniería",
    "Ciencias Biológicas y de la Salud",
    "Ciencias Sociales y Humanidades",
    "Ciencias y Artes para el Diseño"
  ],

  "EXANI II": [
    "Comprensión lectora",
    "Redacción indirecta",
    "Pensamiento matemático",
    "Inglés como lengua extranjera diagnóstico",
    "Administración",
    "Aritmética",
    "Biología",
    "Cálculo diferencial e integral",
    "Ciencias de la salud",
    "Derecho",
    "Economía",
    "Filosofía",
    "Física",
    "Historia",
    "Literatura",
    "Matemáticas financieras",
    "Premedicina",
    "Probabilidad y estadística",
    "Psicología",
    "Química",
    "Ciencias experimentales",
    "Ciencias sociales"
  ],

  "UACH Universidad": [
    "Habilidades numéricas",
    "Habilidades verbales",
    "Matemáticas",
    "Física",
    "Química",
    "Biología",
    "Geografía",
    "Lengua y Literatura",
    "Historia mundial",
    "Historia de México"
  ]
};


function renderizarMatematicas(elemento = document.body) {
  if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
    window.MathJax.typesetPromise([elemento]).catch(error => {
      console.error("Error al renderizar matemáticas:", error);
    });
  }
}

function mostrarSeccion(id) {
  document.querySelectorAll(".seccion, .examen-pantalla").forEach(seccion => {
    seccion.classList.add("oculto");
  });

  document.getElementById(id).classList.remove("oculto");
}

function normalizarNombre(texto) {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ñ/g, "n")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function obtenerRutaSimulador(categoria, numeroSimulador, areaId = "") {
  if (areaId && clavesUniversidad[categoria]) {
    const institucion = clavesUniversidad[categoria];
    return (
      "preguntas_universidad/" +
      institucion + "/" +
      areaId + "/simulador_" +
      numeroSimulador + "_" +
      institucion + "_" +
      areaId + ".json"
    );
  }

  const base = rutasBase[categoria];
  if (!base) return null;
  return base + "simulador_" + numeroSimulador + ".json";
}

function obtenerRutaSimuladorMateria(categoria, materia, numeroSimulador) {
  const categoriaNormalizada = normalizarNombre(categoria);
  const materiaNormalizada = normalizarNombre(materia);

  return (
    "preguntas_materia/" +
    categoriaNormalizada +
    "/" +
    materiaNormalizada +
    "/simulador_" +
    numeroSimulador +
    ".json"
  );
}
async function verificarJsonDisponible(ruta, boton) {
  if (!ruta) {
    boton.classList.add("simulador-pendiente");
    boton.classList.remove("simulador-disponible");
    return;
  }

  try {
    const respuesta = await fetch(ruta + "?v=" + Date.now(), {
      method: "HEAD",
      cache: "no-store"
    });

    if (respuesta.ok) {
      boton.classList.remove("simulador-pendiente");
      boton.classList.add("simulador-disponible");
    } else {
      boton.classList.add("simulador-pendiente");
      boton.classList.remove("simulador-disponible");
    }
  } catch (error) {
    boton.classList.add("simulador-pendiente");
    boton.classList.remove("simulador-disponible");
  }
}
function mostrarAreasUniversidad(nombreCategoria) {
  const titulo = document.getElementById("tituloAreasUniversidad");
  const contenedor = document.getElementById("contenedorAreasUniversidad");

  categoriaActual = nombreCategoria;
  areaUniversidadActual = "";
  ultimaCategoria = "universidad";

  titulo.textContent = nombreCategoria + " - Áreas / módulos";
  contenedor.innerHTML = "";

  const areas = areasUniversidad[nombreCategoria] || [];

  areas.forEach(area => {
    const boton = document.createElement("button");
    boton.className = "boton-lista boton-area-universidad";
    boton.innerHTML = "<strong>" + area.titulo + "</strong><span>" + area.descripcion + "</span>";
    boton.onclick = function () {
      mostrarSimuladoresUniversidad(nombreCategoria, area.id, area.titulo);
    };
    contenedor.appendChild(boton);
  });

  const botonMateria = document.createElement("button");
  botonMateria.className = "boton-materia-especial";
  botonMateria.textContent = "Simulador por materia";
  botonMateria.onclick = function () {
    origenMateriasSimulador = "areasUniversidad";
    mostrarMateriasSimulador(nombreCategoria);
  };
  contenedor.appendChild(botonMateria);

  mostrarSeccion("areasUniversidad");
}

function mostrarSimuladoresUniversidad(categoria, areaId, areaTitulo) {
  const titulo = document.getElementById("tituloSimulador");
  const contenedor = document.getElementById("contenedorSimuladores");

  categoriaActual = categoria;
  areaUniversidadActual = areaId;
  ultimaCategoria = "areasUniversidad";

  titulo.textContent = categoria + " - " + areaTitulo;
  contenedor.innerHTML = "";

  for (let i = 1; i <= 10; i++) {
    const boton = document.createElement("button");
    boton.className = "boton-simulador simulador-pendiente";
    boton.textContent = "Simulador " + i;

    const ruta = obtenerRutaSimulador(categoria, i, areaId);
    boton.onclick = function () {
      abrirConfiguracionExamen(categoria, i, false, "", areaId);
    };

    contenedor.appendChild(boton);
    verificarJsonDisponible(ruta, boton);
  }

  mostrarSeccion("simuladores");
}

function regresarDesdeMaterias() {
  mostrarSeccion(origenMateriasSimulador || "simuladores");
}

function mostrarSimuladores(nombreCategoria, origen) {
  const titulo = document.getElementById("tituloSimulador");
  const contenedor = document.getElementById("contenedorSimuladores");

  categoriaActual = nombreCategoria;
  areaUniversidadActual = "";
  ultimaCategoria = origen;
  origenMateriasSimulador = "simuladores";

  titulo.textContent = "Simuladores - " + nombreCategoria;
  contenedor.innerHTML = "";

  const botonMateria = document.createElement("button");
  botonMateria.className = "boton-materia-especial";
  botonMateria.textContent = "Simulador por materia";
  botonMateria.onclick = function () {
    mostrarMateriasSimulador(nombreCategoria);
  };

  contenedor.appendChild(botonMateria);

  for (let i = 1; i <= 10; i++) {
    const boton = document.createElement("button");
    boton.className = "boton-simulador simulador-pendiente";
    boton.textContent = "Simulador " + i;

    const ruta = obtenerRutaSimulador(nombreCategoria, i);

    boton.onclick = function () {
      abrirConfiguracionExamen(nombreCategoria, i, false);
    };

    contenedor.appendChild(boton);

    verificarJsonDisponible(ruta, boton);
  }

  mostrarSeccion("simuladores");
}

function mostrarMateriasSimulador(categoria) {
  const titulo = document.getElementById("tituloMateriasSimulador");
  const contenedor = document.getElementById("contenedorMaterias");

  titulo.textContent = "Simulador por materia - " + categoria;
  contenedor.innerHTML = "";

  const materias = materiasPorCategoria[categoria] || [];

  materias.forEach(materia => {
    const boton = document.createElement("button");
    boton.className = "boton-lista boton-materia";
    boton.textContent = materia;

    boton.onclick = function () {
      mostrarSimuladoresDeMateria(categoria, materia);
    };

    contenedor.appendChild(boton);
  });

  mostrarSeccion("materiasSimulador");
}

function mostrarSimuladoresDeMateria(categoria, materia) {
  const titulo = document.getElementById("tituloSimuladoresMateria");
  const contenedor = document.getElementById("contenedorSimuladoresMateria");

  categoriaActual = categoria;
  materiaActualSeleccionada = materia;

  titulo.textContent = categoria + " - " + materia;
  contenedor.innerHTML = "";

  for (let i = 1; i <= 10; i++) {
    const boton = document.createElement("button");
    boton.className = "boton-simulador-materia simulador-pendiente";
    boton.textContent = "Simulador " + i;

    const ruta = obtenerRutaSimuladorMateria(categoria, materia, i);

    boton.onclick = function () {
      abrirConfiguracionExamen(categoria, i, true, materia);
    };

    contenedor.appendChild(boton);
    verificarJsonDisponible(ruta, boton);
  }

  mostrarSeccion("simuladoresMateria");
}

function regresarCategoria() {
  mostrarSeccion(ultimaCategoria);
}

function regresarDesdeConfiguracion() {
  if (configuracionEsPorMateria && materiaActualSeleccionada) {
    mostrarSimuladoresDeMateria(categoriaActual, materiaActualSeleccionada);
    return;
  }

  mostrarSeccion("simuladores");
}

async function abrirConfiguracionExamen(categoria, numeroSimulador, esPorMateria = false, materia = "", areaId = "") {
  configuracionEsPorMateria = esPorMateria;
  categoriaActual = categoria;
  if (esPorMateria) materiaActualSeleccionada = materia;
  if (areaId) areaUniversidadActual = areaId;

  const ruta = esPorMateria
    ? obtenerRutaSimuladorMateria(categoria, materia, numeroSimulador)
    : obtenerRutaSimulador(categoria, numeroSimulador, areaId);

  if (!ruta) {
    alert("Esta categoría todavía no tiene ruta configurada.");
    return;
  }

  try {
    const respuesta = await fetch(ruta + "?v=" + Date.now(), {
      cache: "no-store"
    });

    if (!respuesta.ok) {
      alert(
        "Este simulador todavía no tiene JSON cargado.\n\n" +
        "Archivo esperado:\n" +
        ruta
      );
      return;
    }

    examenActual = await respuesta.json();
    preguntas = examenActual.preguntas || [];

    console.log("JSON cargado:", ruta);
    console.log("Nombre:", examenActual.nombre);
    console.log("Institución:", examenActual.institucion);
    console.log("Total preguntas:", preguntas.length);
    console.log("Primera pregunta:", preguntas[0]);

    if (!preguntas.length) {
      alert("El JSON existe, pero no contiene preguntas.");
      return;
    }

    document.getElementById("tituloConfigExamen").textContent =
      examenActual.nombre || "Simulador";

    const duracion = examenActual.configuracion?.duracion_minutos || 180;

    document.getElementById("duracionTexto").textContent =
      "Duración: " + duracion + " minutos";

    document.getElementById("activarContador").checked =
      examenActual.configuracion?.contador_activo_por_defecto || false;

    document.getElementById("activarContador").disabled =
      examenActual.configuracion?.contador_permitido === false;

    const activarRespuestasOcultas = document.getElementById("activarRespuestasOcultas");
    if (activarRespuestasOcultas) {
      activarRespuestasOcultas.checked =
        examenActual.configuracion?.respuestas_ocultas_por_defecto !== false;
    }

    mostrarSeccion("configuracionExamen");
  } catch (error) {
    alert(
      "No se pudo cargar este simulador.\n\n" +
      "Revisa que el JSON esté bien escrito y colocado aquí:\n" +
      ruta
    );
    console.error(error);
  }
}

function iniciarExamenDesdeConfig() {
  preguntaActual = 0;
  respuestasUsuario = {};
  respuestaVisible = null;
  contadorActivado = document.getElementById("activarContador").checked;
  respuestasOcultasActivadas =
    document.getElementById("activarRespuestasOcultas")?.checked ?? true;

  document.getElementById("franjaInstitucion").textContent =
    examenActual?.institucion || "SIM";

  if (contadorIntervalo) {
    clearInterval(contadorIntervalo);
  }

  if (contadorActivado) {
    const duracion = examenActual.configuracion?.duracion_minutos || 180;
    tiempoRestanteSegundos = duracion * 60;

    document.getElementById("contador").classList.remove("oculto");
    actualizarVistaContador();

    contadorIntervalo = setInterval(() => {
      tiempoRestanteSegundos--;
      actualizarVistaContador();

      if (tiempoRestanteSegundos <= 0) {
        clearInterval(contadorIntervalo);
        finalizarExamen(true);
      }
    }, 1000);
  } else {
    document.getElementById("contador").classList.add("oculto");
  }

  mostrarSeccion("examen");
  crearIndicePreguntas();
  cargarPregunta();
}

function actualizarVistaContador() {
  const minutos = Math.floor(tiempoRestanteSegundos / 60);
  const segundos = tiempoRestanteSegundos % 60;

  document.getElementById("contador").textContent =
    String(minutos).padStart(2, "0") + ":" + String(segundos).padStart(2, "0");
}

function crearIndicePreguntas() {
  const contenedor = document.getElementById("indicePreguntas");
  if (!contenedor) return;

  contenedor.innerHTML = "";

  preguntas.forEach((pregunta, indice) => {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "boton-indice-pregunta";
    boton.textContent = indice + 1;
    boton.setAttribute("aria-label", "Ir a la pregunta " + (indice + 1));
    boton.onclick = function () {
      irAPregunta(indice);
    };
    contenedor.appendChild(boton);
  });

  actualizarIndicePreguntas();
}

function actualizarIndicePreguntas() {
  const botones = document.querySelectorAll("#indicePreguntas .boton-indice-pregunta");

  botones.forEach((boton, indice) => {
    boton.classList.toggle("actual", indice === preguntaActual);
    const pregunta = preguntas[indice];
    const respondida = pregunta && respuestasUsuario[pregunta.id] !== undefined;
    boton.classList.toggle("respondida", respondida);
  });
}

function irAPregunta(indice) {
  if (indice < 0 || indice >= preguntas.length) return;
  preguntaActual = indice;
  cargarPregunta();
  document.querySelector(".encabezado-examen")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cargarPregunta() {
  const pregunta = preguntas[preguntaActual];

  document.getElementById("materiaActual").textContent =
    pregunta.materia || "Sin materia";

  document.getElementById("progresoPregunta").textContent =
    "Pregunta " + (preguntaActual + 1) + " de " + preguntas.length;

  respuestaVisible = null;
  actualizarIndicePreguntas();
  mostrarPregunta();
  renderOpciones();
}

function mostrarPregunta() {
  respuestaVisible = null;

  const pregunta = preguntas[preguntaActual];
  const contenedor = document.getElementById("contenidoVisible");

  contenedor.innerHTML = "";

  const numeroPregunta = pregunta.id || preguntaActual + 1;
  const texto = pregunta.pregunta?.contenido || "";

  const parrafo = document.createElement("div");
  parrafo.className = "texto-pregunta";
  parrafo.innerHTML = texto
    ? `<span class="numero-pregunta">${numeroPregunta})</span> ${texto}`
    : `<span class="numero-pregunta">${numeroPregunta})</span> Pregunta sin contenido.`;

  contenedor.appendChild(parrafo);

  if (pregunta.pregunta?.imagen) {
    const imagen = document.createElement("img");
    imagen.src = pregunta.pregunta.imagen;
    imagen.alt = "Imagen de la pregunta " + numeroPregunta;
    contenedor.appendChild(imagen);
  }

  renderizarMatematicas(contenedor);
  renderOpciones();
}

function ocultarPreguntaConBoton() {
  const contenedor = document.getElementById("contenidoVisible");
  contenedor.innerHTML = "";

  const boton = document.createElement("button");
  boton.className = "boton-ver-pregunta";
  boton.textContent = "Ver pregunta";
  boton.onclick = mostrarPregunta;

  contenedor.appendChild(boton);
}

function renderOpciones() {
  const pregunta = preguntas[preguntaActual];
  const contenedor = document.getElementById("zonaOpciones");

  contenedor.innerHTML = "";

  const opciones = pregunta.opciones || [];

  opciones.forEach(opcion => {
    const fila = document.createElement("div");
    fila.className = respuestasOcultasActivadas
      ? "fila-opcion"
      : "fila-opcion fila-opcion-visible";

    const selector = document.createElement("button");
    selector.className = "selector-opcion";
    selector.title = "Elegir " + opcion.inciso;

    if (respuestasUsuario[pregunta.id] === opcion.inciso) {
      selector.classList.add("seleccionada");
    }

    selector.onclick = function () {
      seleccionarRespuesta(opcion.inciso);
    };

    const inciso = document.createElement("div");
    inciso.className = "inciso-opcion";
    inciso.textContent = opcion.inciso + ")";

    fila.append(selector, inciso);

    if (respuestasOcultasActivadas) {
      const botonVer = document.createElement("button");
      botonVer.className = "boton-ver-respuesta";
      botonVer.textContent = "Ver respuesta";
      botonVer.onclick = function () {
        mostrarRespuestaEnFila(opcion.inciso);
      };

      fila.appendChild(botonVer);

      if (respuestaVisible === opcion.inciso) {
        const respuestaDiv = crearContenidoRespuesta(opcion);
        fila.appendChild(respuestaDiv);
      } else {
        fila.appendChild(document.createElement("div"));
      }
    } else {
      const respuestaDiv = crearContenidoRespuesta(opcion);
      respuestaDiv.classList.add("respuesta-visible-directa");
      fila.appendChild(respuestaDiv);
    }

    contenedor.appendChild(fila);
  });

  renderizarMatematicas(contenedor);
}

function crearContenidoRespuesta(opcion) {
  const respuestaDiv = document.createElement("div");
  respuestaDiv.className = "respuesta-desplegada";

  const texto = document.createElement("div");
  texto.className = "texto-opcion";
  texto.innerHTML = opcion.texto || "Opción sin contenido.";
  respuestaDiv.appendChild(texto);

  if (opcion.imagen) {
    const imagen = document.createElement("img");
    imagen.src = opcion.imagen;
    imagen.alt = "Imagen opción " + opcion.inciso;
    respuestaDiv.appendChild(imagen);
  }

  return respuestaDiv;
}

function mostrarRespuestaEnFila(inciso) {
  if (!respuestasOcultasActivadas) return;

  respuestaVisible = inciso;
  ocultarPreguntaConBoton();
  renderOpciones();
}

function seleccionarRespuesta(inciso) {
  const pregunta = preguntas[preguntaActual];
  respuestasUsuario[pregunta.id] = inciso;
  actualizarIndicePreguntas();
  renderOpciones();
}

function preguntaAnterior() {
  if (preguntaActual > 0) {
    preguntaActual--;
    cargarPregunta();
  }
}

function preguntaSiguiente() {
  if (preguntaActual < preguntas.length - 1) {
    preguntaActual++;
    cargarPregunta();
  }
}

function finalizarExamen(finalizadoPorTiempo) {
  if (!finalizadoPorTiempo) {
    const confirmar = window.confirm(
      "¿Estás seguro de que quieres finalizar el examen?\n\nSi finalizas ahora, se calcularán tus resultados y ya no podrás continuar respondiendo."
    );

    if (!confirmar) {
      return;
    }
  }

  if (contadorIntervalo) {
    clearInterval(contadorIntervalo);
  }

  const total = preguntas.length;
  let correctas = 0;
  const porMateria = {};

  preguntas.forEach(pregunta => {
    const materia = pregunta.materia || "Sin materia";

    if (!porMateria[materia]) {
      porMateria[materia] = {
        total: 0,
        correctas: 0
      };
    }

    porMateria[materia].total++;

    if (respuestasUsuario[pregunta.id] === pregunta.respuesta_correcta) {
      correctas++;
      porMateria[materia].correctas++;
    }
  });

  document.getElementById("resumenResultados").innerHTML = `
    <div class="resultado-card">
      <h3>${finalizadoPorTiempo ? "El tiempo terminó." : "Examen finalizado."}</h3>
      <p><strong>Puntaje total:</strong> ${correctas} / ${total}</p>
      <p><strong>Porcentaje:</strong> ${((correctas / total) * 100).toFixed(2)}%</p>
    </div>
  `;

  const contenedorMaterias = document.getElementById("resultadosPorMateria");
  contenedorMaterias.innerHTML = "";

  Object.keys(porMateria).forEach(materia => {
    const datos = porMateria[materia];
    const div = document.createElement("div");

    div.className = "resultado-card";
    div.innerHTML = `
      <strong>${materia}</strong>
      <p>${datos.correctas} / ${datos.total}</p>
    `;

    contenedorMaterias.appendChild(div);
  });

  renderizarMatematicas(document.getElementById("resultados"));
  mostrarSeccion("resultados");
}

function mostrarRevision() {
  const contenedor = document.getElementById("contenedorRevision");
  contenedor.innerHTML = "";

  preguntas.forEach((pregunta, indice) => {
    const usuario = respuestasUsuario[pregunta.id] || "Sin responder";
    const correcta = pregunta.respuesta_correcta || "Sin respuesta configurada";
    const esCorrecta = usuario === pregunta.respuesta_correcta;

    const div = document.createElement("div");
    div.className = "revision-card " + (esCorrecta ? "correcta" : "incorrecta");

    div.innerHTML = `
      <h3>Pregunta ${indice + 1} - ${pregunta.materia || "Sin materia"}</h3>
      <p><strong>Pregunta:</strong> ${pregunta.pregunta?.contenido || "Sin contenido"}</p>
      <p><strong>Tu respuesta:</strong> ${usuario}</p>
      <p><strong>Respuesta correcta:</strong> ${correcta}</p>
      <p><strong>Observaciones:</strong> ${pregunta.observaciones || "Sin observaciones."}</p>
    `;

    contenedor.appendChild(div);
  });

  mostrarSeccion("revision");
}