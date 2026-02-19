#!/usr/bin/env perl

require './zfsmanager-lib.pl';
ReadParse();
my $can_pool_props = has_acl_permission('upool_properties');
my $can_pool_destroy = has_acl_permission('upool_destroy');
my $can_zfs_props = has_acl_permission('uzfs_properties');
my $can_zfs_destroy = has_acl_permission('uzfs_destroy');
my $can_snap_destroy = has_acl_permission('usnap_destroy');

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
print ui_columns_start([ "Device Name", "Label", "State", "Read", "Write", "Cksum", "Model", "Serial", "Temp", "SMART", "Action" ]);
foreach $key (sort {$a <=> $b} (keys %status))
{
	my $smart = get_smart_status($status{$key}{name});
	my ($model, $serial, $temp, undef, $label) = get_disk_details($status{$key}{name});
	my $action = "";
	if ($can_pool_props && $status{$key}{state} !~ /ONLINE/ && $status{$key}{name} !~ /^(mirror|raidz|draid|spare|log|cache|special)/) {
		$action = ui_post_action_link('Replace Disk', 'cmd.cgi',
			{ 'cmd' => 'replace', 'pool' => $status{0}{pool}, 'vdev' => $status{$key}{name}, 'xnavigation' => 1 },
			"Are you sure you want to replace disk ".$status{$key}{name}."?");
	}
	if (($status{$key}{parent} =~ /pool/) && ($key != 0)) {
		print ui_columns_row(["<a href='config-vdev.cgi?pool=".u($status{0}{pool}).'&dev='.$key."&xnavigation=1'>".h($status{$key}{name})."</a>", h($label), h($status{$key}{state}), h($status{$key}{read}), h($status{$key}{write}), h($status{$key}{cksum}), h($model), h($serial), h($temp), $smart, $action]);
	} elsif ($key != 0) {
		print ui_columns_row(["<a href='config-vdev.cgi?pool=".u($status{0}{pool}).'&dev='.$key."&xnavigation=1'>|_".h($status{$key}{name})."</a>", h($label), h($status{$key}{state}), h($status{$key}{read}), h($status{$key}{write}), h($status{$key}{cksum}), h($model), h($serial), h($temp), $smart, $action]);
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
my $pool_task_rows = 0;
if ($can_zfs_props) {
	print ui_table_row("New file system: ", "<a href='create.cgi?create=zfs&parent=".u($in{pool})."&xnavigation=1'>Create file system</a>");
	$pool_task_rows++;
}
if ($can_pool_props) {
	if ($status{0}{scan} =~ /scrub in progress/) {
		print ui_table_row('Scrub ', ui_post_action_link('Stop scrub', 'cmd.cgi',
			{ 'cmd' => 'scrub', 'stop' => 'y', 'pool' => $in{pool}, 'xnavigation' => 1 }));
	} else {
		print ui_table_row('Scrub ', ui_post_action_link('Scrub pool', 'cmd.cgi',
			{ 'cmd' => 'scrub', 'pool' => $in{pool}, 'xnavigation' => 1 },
			"Are you sure you want to scrub pool ".$in{pool}."?"));
	}
	$pool_task_rows++;
	print ui_table_row('Upgrade ', ui_post_action_link('Upgrade pool', 'cmd.cgi',
		{ 'cmd' => 'upgrade', 'pool' => $in{pool}, 'xnavigation' => 1 }));
	$pool_task_rows++;
	print ui_table_row('Export ', ui_post_action_link('Export pool', 'cmd.cgi',
		{ 'cmd' => 'export', 'pool' => $in{pool}, 'xnavigation' => 1 }));
	$pool_task_rows++;
}
if ($can_pool_destroy) {
	print ui_table_row("Destroy ", "<a href='create.cgi?destroy_pool=".u($in{pool})."&xnavigation=1'>Destroy this pool</a>");
	$pool_task_rows++;
}
if (!$pool_task_rows) {
	print ui_table_row("Info", "No actions available for your ACL.");
}
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
	ui_list_snapshots('-rd1 '.$in{'zfs'}, $can_snap_destroy ? 1 : 0);
	my %hash = zfs_get($in{'zfs'}, "all");
	
	#--tasks table--
	print ui_table_start("Tasks", "width=100%", "10");
	my $zfs_task_rows = 0;
	if ($can_zfs_props) {
		my $snap_form = ui_create_snapshot($in{'zfs'});
		if ($snap_form ne '') {
			print ui_table_row("Snapshot: ", $snap_form);
			$zfs_task_rows++;
		}
		print ui_table_row("New file system: ", "<a href='create.cgi?create=zfs&parent=".u($in{'zfs'})."&xnavigation=1'>Create child file system</a>");
		$zfs_task_rows++;
		if (index($in{'zfs'}, '/') != -1) {
			print ui_table_row("Rename: ", "<a href='create.cgi?rename=".u($in{'zfs'})."&xnavigation=1'>Rename ".h($in{'zfs'})."</a>");
			$zfs_task_rows++;
		}
		if ($hash{$in{'zfs'}}{origin}) {
			print ui_table_row("Promote: ", "This file system is a clone, ".
				ui_post_action_link('promote '.$in{zfs}, 'cmd.cgi',
				{ 'cmd' => 'promote', 'zfs' => $in{zfs}, 'xnavigation' => 1 }));
			$zfs_task_rows++;
		}
	}
	if ($can_zfs_destroy) {
		print ui_table_row("Destroy: ", "<a href='create.cgi?destroy_zfs=".u($in{zfs})."&xnavigation=1'>Destroy this file system</a>");
		$zfs_task_rows++;
	}
	if (!$zfs_task_rows) {
		print ui_table_row("Info", "No actions available for your ACL.");
	}
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
if ($can_zfs_props) {
	my $snap_form = ui_create_snapshot($zfs);
	if ($snap_form ne '') { print ui_table_row("Snapshot: ", $snap_form); }
	print ui_table_row("Rename: ", "<a href='create.cgi?rename=".u($in{'snap'})."&xnavigation=1'>Rename ".h($in{'snap'})."</a>");
	print ui_table_row("Send: ", ui_post_action_link('Send '.$in{'snap'}.' to gzip', 'cmd.cgi',
		{ 'cmd' => 'send', 'snap' => $in{'snap'}, 'xnavigation' => 1 }));
	print ui_table_row('Clone:', "<a href='create.cgi?clone=".u($in{snap})."&xnavigation=1'>Clone ".h($in{'snap'})." to new file system</a>");
}
print ui_table_row('Rollback:', "Rollback ".h($zfs)." to ".h($in{'snap'}));
if ($can_snap_destroy) {
	print ui_table_row('Destroy:', ui_post_action_link('Destroy snapshot', 'cmd.cgi',
		{ 'cmd' => 'snpdestroy', 'snapshot' => $in{snap}, 'xnavigation' => 1 }), );
}
	print ui_table_end();
	%parent = find_parent($in{'snap'});
ui_print_footer('status.cgi?zfs='.u($parent{'filesystem'}).'&xnavigation=1', h($parent{'filesystem'}));
}
