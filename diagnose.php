<?php
echo "PHP version: " . phpversion() . PHP_EOL;
echo "allow_url_fopen: " . (ini_get('allow_url_fopen') ? 'ON' : 'OFF (this would break everything)') . PHP_EOL;
echo "openssl extension loaded: " . (extension_loaded('openssl') ? 'YES' : 'NO (this would break all HTTPS requests)') . PHP_EOL;
echo PHP_EOL;

echo "--- Testing plain HTTP (no SSL) ---" . PHP_EOL;
$http_result = @file_get_contents("http://example.com");
echo $http_result ? "SUCCESS - got " . strlen($http_result) . " bytes" . PHP_EOL : "FAILED" . PHP_EOL;

echo PHP_EOL . "--- Testing HTTPS with SSL verification OFF ---" . PHP_EOL;
$context = stream_context_create([
    "ssl" => ["verify_peer" => false, "verify_peer_name" => false]
]);
$https_result = @file_get_contents("https://books.toscrape.com/", false, $context);
echo $https_result ? "SUCCESS - got " . strlen($https_result) . " bytes" . PHP_EOL : "FAILED" . PHP_EOL;

if (!$https_result) {
    $error = error_get_last();
    echo "Last PHP error: " . ($error['message'] ?? 'none captured') . PHP_EOL;
}
