-- ⚙️ RÉGLAGES ------------------------------------------------
set skipPages to 0
set remainingPages to 40
set saveTimeout to 60
set downloadFolder to (POSIX path of (path to downloads folder))
set pageLoadDelay to 3
set pythonScript to "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 " & quoted form of "/Users/wisdomfoli/Projects/mlacare_project/mlacare_backend/send_key_to_safari.py"
-- --------------------------------------------------------------

-- Sauter les pages déjà faites
repeat skipPages times
	my simulateRightArrow()
	delay pageLoadDelay
end repeat

repeat with i from 1 to remainingPages
	-- 1. Lister les .html déjà présents AVANT la sauvegarde
	set beforeFiles to my listHTMLFiles(downloadFolder)
	
	-- 2. Envoyer Cmd+Shift+Y à Safari via Python (sans focus)
	do shell script pythonScript
	
	-- 3. Attendre la création et la fin d'écriture du nouveau fichier
	my waitForNewFile(downloadFolder, beforeFiles, saveTimeout)
	
	-- 4. Petite pause de sécurité
	delay 0.5
	
	-- 5. Passer à la page suivante (sauf si c'était la dernière)
	if i < remainingPages then
		my simulateRightArrow()
		delay pageLoadDelay
	end if
end repeat

display notification "Automatisation terminée (" & remainingPages & " pages sauvegardées)" with title "SingleFile"

-- ============================================================
-- SOUS-ROUTINES
-- ============================================================

on listHTMLFiles(folderPath)
	try
		return paragraphs of (do shell script "ls -t " & quoted form of folderPath & "*.html 2>/dev/null")
	on error
		return {}
	end try
end listHTMLFiles

on waitForNewFile(folderPath, beforeFiles, timeoutSeconds)
	set startTime to current date
	set newFile to ""
	
	repeat
		set currentFiles to my listHTMLFiles(folderPath)
		repeat with aFile in currentFiles
			set aFileStr to aFile as string
			if aFileStr is not in beforeFiles then
				set newFile to aFileStr
				exit repeat
			end if
		end repeat
		if newFile is not "" then exit repeat
		if (current date) - startTime > timeoutSeconds then
			display dialog "Aucun nouveau fichier .html créé par SingleFile dans le délai de " & timeoutSeconds & " secondes." buttons {"Arrêter"} default button 1 with icon stop
			error number -128
		end if
		delay 0.5
	end repeat
	
	set stableCount to 0
	set previousSize to -1
	repeat
		try
			set currentSize to (do shell script "stat -f%z " & quoted form of newFile) as integer
		on error
			set currentSize to -1
		end try
		if currentSize = previousSize and currentSize > 0 then
			set stableCount to stableCount + 1
			if stableCount ≥ 4 then exit repeat
		else
			set stableCount to 0
		end if
		set previousSize to currentSize
		if (current date) - startTime > timeoutSeconds then
			display dialog "Le fichier " & newFile & " n'a pas terminé d'être écrit à temps." buttons {"Arrêter"} default button 1 with icon stop
			error number -128
		end if
		delay 0.5
	end repeat
end waitForNewFile

on simulateRightArrow()
	tell application "Safari"
		do JavaScript "
			var el = document.activeElement || document.body;
			['keydown','keyup'].forEach(function(type){
				el.dispatchEvent(new KeyboardEvent(type, {
					key: 'ArrowRight',
					code: 'ArrowRight',
					keyCode: 39,
					which: 39,
					bubbles: true,
					cancelable: true
				}));
			});
		" in current tab of front window
	end tell
end simulateRightArrow
