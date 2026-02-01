#!/usr/bin/perl

require './zfsmanager-lib.pl';
ReadParse();

#show pool status
if ($in{'pool'})
{
if ($in{'pool'} !~ /^[a-zA-Z0-9\.\-\_]+$/) { error($text{'error_invalid_pool'} || "Invalid pool name"); }
ui_print_header(undef, $text{'status_title'}, "", undef, 1, 1);

#Show pool information
ui_zpool_list($in{'pool'});

#show properties for pool
ui_zpool_properties($in{'pool'});

#Show associated file systems

ui_zfs_list("-r ".$in{'pool'});

#Show device configuration
#TODO: show devices by vdev hierarchy
my %status = zpool_status($in{'pool'});
if (scalar(keys %status) > 1) {
print ui_columns_start([ "Device Name", "State", "Read", "Write", "Cksum", "Model", "Serial", "Temp", "SMART", "Action" ]);
foreach $key (sort {$a <=> $b} (keys %status))
{
	my $smart = get_smart_status($status{$key}{name});
	my ($model, $serial, $temp) = get_disk_details($status{$key}{name});
	my $action = "";
	if ($status{$key}{state} !~ /ONLINE/ && $status{$key}{name} !~ /^(mirror|raidz|draid|spare|log|cache|special)/) {
		my $pool_q = u($status{0}{pool});
		my $vdev_q = u($status{$key}{name});
		my $vdev_js = js_escape($status{$key}{name});
		$action = "<a href='cmd.cgi?cmd=replace&pool=$pool_q&vdev=$vdev_q&xnavigation=1' onClick='return confirm(\"Are you sure you want to replace disk $vdev_js?\")'>Replace Disk</a>";
	}
	if (($status{$key}{parent} =~ /pool/) && ($key != 0)) {
		print ui_columns_row(["<a href='config-vdev.cgi?pool=".u($status{0}{pool}).'&dev='.$key."&xnavigation=1'>".h($status{$key}{name})."</a>", h($status{$key}{state}), h($status{$key}{read}), h($status{$key}{write}), h($status{$key}{cksum}), h($model), h($serial), h($temp), $smart, $action]);
	} elsif ($key != 0) {
		print ui_columns_row(["<a href='config-vdev.cgi?pool=".u($status{0}{pool}).'&dev='.$key."&xnavigation=1'>|_".h($status{$key}{name})."</a>", h($status{$key}{state}), h($status{$key}{read}), h($status{$key}{write}), h($status{$key}{cksum}), h($model), h($serial), h($temp), $smart, $action]);
	}
	
}
print ui_columns_end();
}
print ui_table_start("Status", "width=100%", 2, [ { 'width' => '15%' }, { 'width' => '85%' } ]);
print ui_table_row("<b>Scan:</b>", h($status{0}{scan}));
print ui_table_row("<b>Read:</b>", h($status{0}{read}));
print ui_table_row("<b>Write:</b>", h($status{0}{write}));
print ui_table_row("<b>Checksum:</b>", h($status{0}{cksum}));
print ui_table_row("<b>Errors:</b>", h($status{0}{errors}));
print ui_table_end();

if ($status{0}{status} or $status{0}{action} or $status{pool}{see}) {
	print ui_table_start("Attention", "width=100%", "10");
	if ($status{0}{status}) { print ui_table_row("Status:", h($status{0}{status})); }
	if ($status{0}{action}) { print ui_table_row("Action:", h($status{0}{action})); }
	if ($status{0}{see}) { print ui_table_row("See:", h($status{0}{see})); }
	print ui_table_end();
}
	

#--tasks table--
print ui_table_start("Tasks", "width=100%", "10", ['align=left'] );
print ui_table_row("New file system: ", "<a href='create.cgi?create=zfs&parent=".u($in{pool})."&xnavigation=1'>Create file system</a>"); 
if ($status{0}{scan} =~ /scrub in progress/) { print ui_table_row('Scrub ',"<a href='cmd.cgi?cmd=scrub&stop=y&pool=".u($in{pool})."&xnavigation=1'>Stop scrub</a>"); } 
else {
	my $pool_js = js_escape($in{pool});
	print ui_table_row('Scrub ', "<a href='cmd.cgi?cmd=scrub&pool=".u($in{pool})."&xnavigation=1' onClick='return confirm(\"Are you sure you want to scrub pool $pool_js?\")'>Scrub pool</a>");
}
print ui_table_row('Upgrade ', "<a href='cmd.cgi?cmd=upgrade&pool=".u($in{pool})."&xnavigation=1'>Upgrade pool</a>");
print ui_table_row('Export ',  "<a href='cmd.cgi?cmd=export&pool=".u($in{pool})."&xnavigation=1'>Export pool</a>");
print ui_table_row("Destroy ", "<a href='create.cgi?destroy_pool=".u($in{pool})."&xnavigation=1'>Destroy this pool</a>");
print ui_table_end();

ui_print_footer('index.cgi?xnavigation=1', $text{'index_return'});
}

#show filesystem status
if ($in{'zfs'})
{
	if ($in{'zfs'} !~ /^[a-zA-Z0-9\.\-\_\/\@]+$/) { error($text{'error_invalid_zfs'} || "Invalid filesystem name"); }
	ui_print_header(undef, "ZFS File System", "", undef, 1, 1);
	#start status tab
	ui_zfs_list($in{'zfs'});

	#show properties for filesystem
	ui_zfs_properties($in{'zfs'});

	#show child filesystems
	print "<h4>$text{'zfs_children'}</h4>";
	ui_zfs_list("-r -d1 ".$in{'zfs'}, undef, $in{'zfs'});
	
	#show list of snapshots based on filesystem
	ui_list_snapshots('-rd1 '.$in{'zfs'}, 1);
	my %hash = zfs_get($in{'zfs'}, "all");
	
	#--tasks table--
	print ui_table_start("Tasks", "width=100%", "10");
	print ui_table_row("Snapshot: ", ui_create_snapshot($in{'zfs'}));
print ui_table_row("New file system: ", "<a href='create.cgi?create=zfs&parent=".u($in{'zfs'})."&xnavigation=1'>Create child file system</a>"); 
if (index($in{'zfs'}, '/') != -1) { print ui_table_row("Rename: ", "<a href='create.cgi?rename=".u($in{'zfs'})."&xnavigation=1'>Rename ".h($in{'zfs'})."</a>"); }
if ($hash{$in{'zfs'}}{origin}) { print ui_table_row("Promote: ", "This file system is a clone, <a href='cmd.cgi?cmd=promote&zfs=".u($in{zfs})."&xnavigation=1'>promote ".h($in{zfs})."</a>"); }
print ui_table_row("Destroy: ", "<a href='create.cgi?destroy_zfs=".u($in{zfs})."&xnavigation=1'>Destroy this file system</a>");
	print ui_table_end();
	ui_print_footer('index.cgi?mode=zfs&xnavigation=1', $text{'zfs_return'});
	
}

#show snapshot status
#show status of current snapshot
if ($in{'snap'})
{
	if ($in{'snap'} !~ /^[a-zA-Z0-9\.\-\_\/\@]+$/) { error($text{'error_invalid_snap'} || "Invalid snapshot name"); }
	ui_print_header(undef, $text{'snapshot_title'}, "", undef, 1, 1);
	%snapshot = list_snapshots($in{'snap'});
	print ui_columns_start([ "Snapshot", "Used", "Refer" ]);
	foreach $key (sort(keys %snapshot)) 
	{
		my $snap_name = $snapshot{$key}{name};
		print ui_columns_row(["<a href='status.cgi?snap=".u($snap_name)."&xnavigation=1'>".h($snap_name)."</a>", h($snapshot{$key}{used}), h($snapshot{$key}{refer}) ]);
	}
	print ui_columns_end();
	ui_zfs_properties($in{'snap'});

	my $zfs = $in{'snap'};
	$zfs =~ s/\@.*//;
	
	#--tasks table--
	print ui_table_start('Tasks', 'width=100%', undef);
print ui_table_row('Differences', "<a href='diff.cgi?snap=".u($in{snap})."&xnavigation=1'>Show differences in ".h($in{'snap'})."</a>");
print ui_table_row("Snapshot: ", ui_create_snapshot($zfs));
print ui_table_row("Rename: ", "<a href='create.cgi?rename=".u($in{'snap'})."&xnavigation=1'>Rename ".h($in{'snap'})."</a>");
print ui_table_row("Send: ", "<a href='cmd.cgi?cmd=send&snap=".u($in{'snap'})."&xnavigation=1'>Send ".h($in{'snap'})." to gzip</a>");
print ui_table_row('Clone:', "<a href='create.cgi?clone=".u($in{snap})."&xnavigation=1'>Clone ".h($in{'snap'})." to new file system</a>"); 
print ui_table_row('Rollback:', "Rollback ".h($zfs)." to ".h($in{'snap'}));
print ui_table_row('Destroy:',"<a href='cmd.cgi?cmd=snpdestroy&snapshot=".u($in{snap})."&xnavigation=1'>Destroy snapshot</a>", );
	print ui_table_end();
	%parent = find_parent($in{'snap'});
ui_print_footer('status.cgi?zfs='.u($parent{'filesystem'}).'&xnavigation=1', h($parent{'filesystem'}));
}
