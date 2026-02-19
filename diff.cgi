#!/usr/bin/env perl

require './zfsmanager-lib.pl';
ReadParse();
use Data::Dumper;

if (!$in{'snap'} || !is_valid_zfs_name($in{'snap'}) || index($in{'snap'}, '@') == -1) {
	error($text{'error_invalid_snap'} || "Invalid snapshot name");
}

ui_print_header(undef, $text{'diff_title'}, "", undef, 1, 1);

print "Snapshot: ".h($in{'snap'});
@array = grep { defined($_) && $_ ne '' } diff($in{'snap'}, undef);
%type = ('B' => 'Block device', 'C' => 'Character device', '/' => 'Directory', '>' => 'Door', 'F' => 'Regular file');
%action = ('-' => 'removed', '+' => 'created', 'M' => 'Modified', 'R' => 'Renamed');
if (@array) {
	print ui_columns_start([ "File", "Action", "Type" ]);
	foreach $key (@array)
	{
		@file = split("\t", $key);
		print ui_columns_row([ h($file[2]), h($action{@file[0]}), h($type{@file[1]}) ]);
	}
	print ui_columns_end();
} else {
	print "<br />No differences found.<br />";
}

ui_print_footer("status.cgi?snap=".u($in{'snap'}), h($in{'snap'}));
