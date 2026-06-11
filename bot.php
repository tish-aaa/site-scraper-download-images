<?php
// --- CONFIGURATION ---
$searchQuery = $argv[1] ?? ''; // Use terminal argument or default
$baseUrl = "https://www.donedeal.ie/cars";         // CHANGE THIS to the target site
$searchUrl = $baseUrl . "+" . $searchQuery;
$logFile = "activity.log";
$maxResults = 5;       // Safety limit: only process first 5 search results
$delaySeconds = 2;     // "Polite" delay to act like a human

// --- LOGGER FUNCTION ---
function logger($message, $file) {
    $timestamp = date("H:i:s");
    $formatted = "[$timestamp] $message" . PHP_EOL;
    echo $formatted; 
    file_put_contents($file, $formatted, FILE_APPEND);
}

logger("--- Starting Scrape for: $searchUrl ---", $logFile);

$context = stream_context_create([
    "http" => [
        "method" => "GET",
        "header" => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36\r\n" .
                    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\n" .
                    "Accept-Language: en-US,en;q=0.5\r\n" .
                    "Referer: https://www.google.com/\r\n" .
                    "Connection: keep-alive\r\n",
        "follow_location" => 1,
        "timeout" => 30
    ],
    "ssl" => [
        "verify_peer" => false, // This ignores SSL certificate errors which often stop PHP
        "verify_peer_name" => false,
    ]
]);

// 1. FETCH SEARCH PAGE
$searchHtml = @file_get_contents($searchUrl, false, $context);
if (!$searchHtml) {
    logger("FATAL: Could not reach $baseUrl. Check your internet or URL.", $logFile);
    exit;
}

$dom = new DOMDocument();
@$dom->loadHTML($searchHtml);
$xpath = new DOMXPath($dom);

// 2. FIND RESULT LINKS (Update '@class' to match the site's actual HTML)
$resultLinks = $xpath->query("//a[contains(@class, 'result-link')]");
$processedCount = 0;

foreach ($resultLinks as $link) {
    if ($processedCount >= $maxResults) break;

    $relativeUrl = $link->getAttribute('href');
    if (empty($relativeUrl)) continue;

    $parsedBase = parse_url($baseUrl);
    $hostUrl = $parsedBase['scheme'] . "://" . $parsedBase['host'];
    
    $fullUrl = str_starts_with($relativeUrl, 'http') ? $relativeUrl : $hostUrl . $relativeUrl;
    
    $title = trim($link->nodeValue) ?: "listing_" . uniqid();
    
    $folderName = preg_replace('/[^A-Za-z0-9 _-]/', '', $title);
    if (!is_dir($folderName)) {
        mkdir($folderName, 0777, true);
    }

    logger("Processing: $title", $logFile);

    // 3. ENTER SUB-PAGE
    $itemHtml = @file_get_contents($fullUrl, false, $context);
    if ($itemHtml) {
        $itemDom = new DOMDocument();
        @$itemDom->loadHTML($itemHtml);
        $itemXpath = new DOMXPath($itemDom);

        // 4. FIND CAROUSEL IMAGES
        $images = $itemXpath->query("//div[contains(@id, 'carousel')]//img");
        
        $imgCount = 1;
        foreach ($images as $img) {
            $imgUrl = $img->getAttribute('src');
            if (!str_starts_with($imgUrl, 'http')) $imgUrl = $baseUrl . $imgUrl;

            // Download and Save
            $imgData = @file_get_contents($imgUrl, false, $context);
            if ($imgData) {
                file_put_contents("$folderName/$imgCount.jpg", $imgData);
                logger("  -> Saved $imgCount.jpg", $logFile);
                $imgCount++;
            }
            
            usleep(500000); // 0.5 second pause between individual images to avoid getting recognised as a bot
        }
    }

    $processedCount++;
    logger("Waiting $delaySeconds seconds before next result...", $logFile);
    sleep($delaySeconds); // pause between search results
}

logger("--- Task Finished Successfully ---", $logFile);
