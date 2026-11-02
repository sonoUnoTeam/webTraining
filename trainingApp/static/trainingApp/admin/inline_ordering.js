/*
 * Inlines ordenables de Unfold: el molde vacío del formset (clase "empty-form", del que se clonan las
 * filas nuevas) es un hijo más del contenedor que ordena SortableJS y contiene el botón "Agregar ...
 * adicional" (tablas) o lo tiene justo después (tarjetas). Al arrastrar una fila hasta abajo quedaba
 * debajo del botón. Cada vez que cambian los hijos del contenedor (carga, arrastre, fila nueva) se
 * devuelven el molde y el botón al final; las filas reales conservan su orden relativo.
 * Se busca por la clase y no por el id "<prefijo>-empty": si el inline no permite agregar, Unfold le
 * pone ese id a la última fila real.
 */
(function () {
    function directChild(container, element) {
        while (element && element.parentElement !== container) {
            element = element.parentElement;
        }
        return element;
    }

    function keepTemplateLast(container) {
        var tail = [
            directChild(container, container.querySelector('.empty-form')),
            container.querySelector(':scope > .add-row'),
        ].filter(Boolean);
        var children = container.children;
        var alreadyLast = tail.every(function (element, index) {
            return children[children.length - tail.length + index] === element;
        });
        if (!alreadyLast) {
            tail.forEach(function (element) {
                container.appendChild(element);
            });
        }
    }

    // Las filas nuevas se clonan del molde, que en las tablas también recibe un número al arrastrar: todas las
    // agregadas después de un arrastre llegarían con el mismo orden (empate). Con 0 el modelo las ubica al final,
    // en el orden en que se agregaron, que es donde se ven.
    document.addEventListener('formset:added', function (event) {
        var container = event.target.closest('[data-ordering-field]');
        if (!container) {
            return;
        }
        var suffix = '-' + container.dataset.orderingField;
        event.target.querySelectorAll('input[name$="' + suffix + '"]').forEach(function (input) {
            input.value = '0';
        });
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-ordering-field]').forEach(function (container) {
            keepTemplateLast(container);
            new MutationObserver(function () {
                keepTemplateLast(container);
            }).observe(container, {childList: true});
        });
    });
})();
