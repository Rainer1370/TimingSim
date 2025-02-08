<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<databrowser>
    <title>PID Gains Plot</title>
    <save_changes>true</save_changes>
    <show_legend>true</show_legend>
    <show_toolbar>true</show_toolbar>
    <grid>true</grid>
    <scroll>true</scroll>
    <update_period>1.0</update_period>
    <scroll_step>5</scroll_step>
    <start>-600 sec</start>
    <end>now</end>
    <archive_rescale>NONE</archive_rescale>
    <background>
        <red>255</red>
        <green>255</green>
        <blue>255</blue>
    </background>
    <title_font>Liberation Sans|20|1</title_font>
    <label_font>Liberation Sans|14|1</label_font>
    <scale_font>Liberation Sans|12|0</scale_font>
    <legend_font>Liberation Sans|14|0</legend_font>
    <axes>
        <axis>
            <visible>true</visible>
            <name>PID Gains</name>
            <use_axis_name>true</use_axis_name>
            <right>false</right>
            <color>
                <red>0</red>
                <green>0</green>
                <blue>0</blue>
            </color>
            <autoscale>true</autoscale>
            <log_scale>false</log_scale>
        </axis>
    </axes>
    <pvlist>
        <pv>
            <display_name>SIM:PID:Kp</display_name>
            <visible>true</visible>
            <name>SIM:PID:Kp</name>
            <axis>0</axis>
            <color>
                <red>255</red>
                <green>0</green>
                <blue>0</blue>
            </color>
            <trace_type>LINE</trace_type>
            <linewidth>2</linewidth>
            <point_type>NONE</point_type>
            <point_size>2</point_size>
        </pv>
        <pv>
            <display_name>SIM:PID:Ki</display_name>
            <visible>true</visible>
            <name>SIM:PID:Ki</name>
            <axis>0</axis>
            <color>
                <red>0</red>
                <green>255</green>
                <blue>0</blue>
            </color>
            <trace_type>LINE</trace_type>
            <linewidth>2</linewidth>
            <point_type>NONE</point_type>
            <point_size>2</point_size>
        </pv>
        <pv>
            <display_name>SIM:PID:Kd</display_name>
            <visible>true</visible>
            <name>SIM:PID:Kd</name>
            <axis>0</axis>
            <color>
                <red>0</red>
                <green>0</green>
                <blue>255</blue>
            </color>
            <trace_type>LINE</trace_type>
            <linewidth>2</linewidth>
            <point_type>NONE</point_type>
            <point_size>2</point_size>
        </pv>
    </pvlist>
</databrowser>
