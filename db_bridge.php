<?php
// ============================================================
// db_bridge.php  — upload this to your server root directory
// ============================================================

// Secret key — Python must send this exact value
define('SECRET', 'your_opencart_secret_key');

// Reject requests without the correct secret
if (!isset($_POST['secret']) || $_POST['secret'] !== SECRET) {
    http_response_code(403);
    die(json_encode(['error' => 'Forbidden']));
}

// ============================================================
// IMAGE UPLOAD (new — handles file uploads from Python)
// ============================================================
if (isset($_FILES['file'])) {
    $IMAGE_DIR = __DIR__ . '/image/';
    $target_rel_path = $_POST['path'] ?? '';

    if (empty($target_rel_path)) {
        die(json_encode(['error' => 'No target path provided']));
    }

    $target_full_path = $IMAGE_DIR . $target_rel_path;
    $target_folder = dirname($target_full_path);

    if (!is_dir($target_folder)) {
        mkdir($target_folder, 0755, true);
    }

    if (move_uploaded_file($_FILES['file']['tmp_name'], $target_full_path)) {
        echo json_encode(['status' => 'success', 'message' => "File saved to $target_rel_path"]);
    } else {
        echo json_encode(['error' => "Failed to save file to disk"]);
    }
    exit;
}

// ============================================================
// SQL QUERIES 
// ============================================================

// DB credentials (same as OpenCart config.php)
$host = 'localhost';
$port = 3306;
$user = 'your_username';
$password = 'your_password';
$database = 'your_database';
// Connect
$conn = new mysqli($host, $user, $password, $database, $port);
if ($conn->connect_error) {
    http_response_code(500);
    die(json_encode(['error' => 'DB connection failed: ' . $conn->connect_error]));
}
$conn->set_charset('utf8mb4');

// Run the query sent from Python
$sql = $_POST['query'] ?? '';
if (empty($sql)) {
    die(json_encode(['error' => 'No query provided']));
}

$result = $conn->query($sql);

if ($result === false) {
    die(json_encode(['error' => 'Query error: ' . $conn->error]));
}

// SELECT → return rows
if ($result instanceof mysqli_result) {
    $rows = [];
    while ($row = $result->fetch_assoc()) {
        $rows[] = $row;
    }
    echo json_encode(['data' => $rows, 'count' => count($rows)]);
} else {
    // INSERT / UPDATE / DELETE → return affected rows
    echo json_encode([
        'affected_rows' => $conn->affected_rows,
        'insert_id' => $conn->insert_id,
    ]);
}

$conn->close();
?>
