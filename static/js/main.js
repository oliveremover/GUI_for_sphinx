$(document).ready(function() {
    // Initialize jstree for content tree data
    contentTreeData.forEach(function(tree, index) {
        $('#jstree-content-' + (index + 1)).jstree({
            'core': {
                'data': tree,
                'check_callback': true
            },
            'plugins': ['dnd']
        });

        $('#jstree-content-' + (index + 1)).on("select_node.jstree", function (e, data) {
            var href = data.node.a_attr.href;
            if (href) {
                window.location.href = href;
            }
        });

        // Save the new order when nodes are moved
        $('#jstree-content-' + (index + 1)).on('move_node.jstree', function (e, data) {
            var newOrder = $('#jstree-content-' + (index + 1)).jstree(true).get_json('#', {flat: true});
            $.ajax({
                type: 'POST',
                url: '/save_order',
                contentType: 'application/json',
                data: JSON.stringify(newOrder),
                success: function(response) {
                    console.log('Order saved successfully');
                },
                error: function(error) {
                    console.error('Error saving order:', error);
                }
            });
        });
    });

    // Initialize jstree for started tree data
    startedTreeData.forEach(function(tree, index) {
        $('#jstree-started-' + (index + 1)).jstree({
            'core': {
                'data': tree,
                'check_callback': true
            },
            'plugins': ['dnd']
        });

        $('#jstree-started-' + (index + 1)).on("select_node.jstree", function (e, data) {
            var href = data.node.a_attr.href;
            if (href) {
                window.location.href = href;
            }
        });

        // Save the new order when nodes are moved
        $('#jstree-started-' + (index + 1)).on('move_node.jstree', function (e, data) {
            var newOrder = $('#jstree-started-' + (index + 1)).jstree(true).get_json('#', {flat: true});
            $.ajax({
                type: 'POST',
                url: '/save_order',
                contentType: 'application/json',
                data: JSON.stringify(newOrder),
                success: function(response) {
                    console.log('Order saved successfully');
                },
                error: function(error) {
                    console.error('Error saving order:', error);
                }
            });
        });
    });

    // Populate folder dropdowns
    function populateFolderDropdown(treeData, parentPath = '') {
        treeData.forEach(function(node) {
            if (node.children) {
                var folderPath = parentPath + '/' + node.text;
                $('#folder-select').append(new Option(folderPath, folderPath));
                $('#parent-folder-select').append(new Option(folderPath, folderPath));
                $('#delete-folder-select').append(new Option(folderPath, folderPath));
                populateFolderDropdown(node.children, folderPath);
            }
        });
    }

    contentTreeData.forEach(function(tree) {
        populateFolderDropdown(tree);
    });

    startedTreeData.forEach(function(tree) {
        populateFolderDropdown(tree);
    });
});