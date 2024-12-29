var checkboxes = document.querySelectorAll("input[type=checkbox][name=chart]");
var changed = false
var selectedOptions = [];
var tabId = 'reliance-tab';

checkboxes.forEach(function(checkbox) {
    checkbox.addEventListener('change', function() {
        selectedOptions = []
        changed = true
        $('input[name="chart"]:checked').each(function () {
            selectedOptions.push($(this).val());
        });
        console.log(selectedOptions)
        for (var key in stock_called){
            stock_called[key] = false;
        }
        // document.querySelector('#'+tabId).click();
        plot_stock1();
        plot_stock2();
    });
})

document.addEventListener('DOMContentLoaded', function () {
    var tabsElement = document.querySelector('.tabs');
    plot_stock1();
    tabsElement.addEventListener('show.bs.tab', function (event) {
        tabId = event.target.getAttribute('id');
        console.log('Currently shown tab ID:', tabId);
    });
});
